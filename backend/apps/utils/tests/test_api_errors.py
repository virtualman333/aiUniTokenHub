"""`first_error_message` 的单元测试 —— 纯 Python，不需要数据库、不需要 Django settings。

这边钉的是**一句给人看的话**，它的输入却是个形状不定的东西（DRF 的 `serializer.errors`）。
所以这里分三段：

1. **正常形态**：结果必须与旧写法一字不差（13 处调用点换过去之后，用户看不到任何变化）。
2. **坏形状**：嵌套 dict、`many=True` 的 list、空的、None —— 一个都不许抛。
   这些形态全都发生在「用户填错了表单」这条路径上，抛出去就是 500。
3. **反向对照**：把旧写法逐字照抄进来，断言它在这些形态上**真的会出事** ——
   免得日后有人觉得这个模块是多余的搬运，把调用点改回那一行。
"""
import unittest

from apps.utils.api_errors import DEFAULT_MESSAGE, first_error_message


def old_first_error(errors):
    """13 处调用点原来的写法，逐字照抄（`apps/*/views.py` 里那行）。

    只在本测试里当反向对照用：`apps/*/views.py` 现在一处都不留
    （只剩本文件与 `api_errors.py` 的文档引用）。
    """
    return list(errors.values())[0][0] if errors else '参数错误'


class TestFirstErrorMessage(unittest.TestCase):
    # ---- 1. 正常形态：与旧写法一字不差 ----

    def test_单字段单消息(self):
        errors = {'username': ['这个字段是必填项。']}
        self.assertEqual(first_error_message(errors), '这个字段是必填项。')
        self.assertEqual(first_error_message(errors), old_first_error(errors))

    def test_多字段取第一个字段的消息(self):
        errors = {'username': ['这个字段是必填项。'], 'password': ['密码太短。']}
        self.assertEqual(first_error_message(errors), '这个字段是必填项。')
        self.assertEqual(first_error_message(errors), old_first_error(errors))

    def test_同一字段多条消息取第一条(self):
        errors = {'password': ['密码太短。', '密码不能全是数字。']}
        self.assertEqual(first_error_message(errors), '密码太短。')
        self.assertEqual(first_error_message(errors), old_first_error(errors))

    def test_non_field_errors_形态(self):
        errors = {'non_field_errors': ['手机号或密码错误。']}
        self.assertEqual(first_error_message(errors), '手机号或密码错误。')

    def test_ErrorDetail_原样返回(self):
        # DRF 的 ErrorDetail 是 str 的子类，str() 之后就是那句话
        class ErrorDetail(str):
            pass

        errors = {'code': [ErrorDetail('验证码已过期。')]}
        self.assertEqual(first_error_message(errors), '验证码已过期。')

    # ---- 2. 坏形状：一个都不许抛 ----

    def test_嵌套_dict_不抛且取到里面的消息(self):
        errors = {'items': {0: {'name': ['必填']}}}
        self.assertEqual(first_error_message(errors), '必填')

    def test_many_True_的_list_形态(self):
        errors = [{'name': ['必填']}, {'age': ['必须大于 0']}]
        self.assertEqual(first_error_message(errors), '必填')

    def test_值是_dict_且为空时继续找下一个字段(self):
        errors = {'a': {}, 'b': ['第二条字段才有话说']}
        self.assertEqual(first_error_message(errors), '第二条字段才有话说')

    def test_空白消息会被跳过而不是当成结果(self):
        errors = {'a': ['   '], 'b': ['有话说']}
        self.assertEqual(first_error_message(errors), '有话说')

    def test_空_dict_给兜底话术(self):
        self.assertEqual(first_error_message({}), DEFAULT_MESSAGE)

    def test_空_list_给兜底话术(self):
        self.assertEqual(first_error_message([]), DEFAULT_MESSAGE)

    def test_None_给兜底话术(self):
        self.assertEqual(first_error_message(None), DEFAULT_MESSAGE)

    def test_值里的_None_给兜底话术(self):
        self.assertEqual(first_error_message({'a': None}), DEFAULT_MESSAGE)

    def test_可以换兜底话术(self):
        self.assertEqual(first_error_message({}, default='参数有误'), '参数有误')

    def test_很深的嵌套也不炸(self):
        errors = {'a': [[[[{'b': ['深']}]]]]}
        self.assertEqual(first_error_message(errors), '深')

    # ---- 3. 反向对照：旧写法在坏形状上真的会出事（实测，不是推测） ----
    #
    # 这段的期望值是**跑出来的**：`{'items': {0: ...}}` 里恰好有整数键 0，所以旧写法
    # 不抛 —— 它返回那个 dict，调用方紧接着 `str()` 出去，用户看到的是
    # "{'name': ['必填']}" 这种 Python 字面量。坏法有两种（崩 / 给垃圾文案），都要钉。

    def test_反向对照_旧写法在嵌套形态上把_dict_当消息返回(self):
        errors = {'items': {0: {'name': ['必填']}}}
        got = old_first_error(errors)
        self.assertIsInstance(got, dict, '旧写法在嵌套形态下会返回一个 dict')
        self.assertEqual(str(got), "{'name': ['必填']}", '这就是用户会看到的东西')

    def test_反向对照_旧写法在只有第二项报错时抛_KEYERROR(self):
        # DRF 的列表字段用整数下标做键，且只报出错的那几项 —— 第一项没错时键 0 不存在
        errors = {'items': {1: ['必填']}}
        with self.assertRaises(KeyError):
            old_first_error(errors)
        self.assertEqual(first_error_message(errors), '必填')

    def test_反向对照_旧写法在_list_形态上抛_AttributeError(self):
        errors = [{'name': ['必填']}]
        with self.assertRaises(AttributeError):
            old_first_error(errors)

    def test_反向对照_旧写法在空列表值上抛_IndexError(self):
        # `{'a': []}` 是**真值**（dict 非空），于是走到 `[0]`，而里面是空的
        errors = {'a': []}
        with self.assertRaises(IndexError):
            old_first_error(errors)

    def test_反向对照_旧写法在正常形态上与新函数一致(self):
        # 这一条保证「换过去以后用户看不到变化」—— 反向对照的另一半
        for errors in (
            {'username': ['必填']},
            {'a': ['一'], 'b': ['二']},
            {'password': ['短', '太简单']},
        ):
            self.assertEqual(first_error_message(errors), old_first_error(errors))


if __name__ == '__main__':
    unittest.main()
