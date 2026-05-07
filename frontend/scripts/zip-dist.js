#!/usr/bin/env node
import { createWriteStream, existsSync, readdirSync, statSync, readFileSync } from 'fs';
import { join, relative, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createGzip } from 'zlib';
import { pipeline } from 'stream/promises';
import dayjs from 'dayjs';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const distPath = join(__dirname, '../dist');
const outputPath = join(__dirname, '../');

if (!existsSync(distPath)) {
  console.error('Error: dist directory not found. Please run "npm run build" first.');
  process.exit(1);
}

const zipFileName = `dist.zip`;

// 简单的 ZIP 实现，不依赖外部库
class SimpleZip {
  constructor() {
    this.files = [];
    this.centralDirectory = [];
    this.offset = 0;
  }

  addFile(path, content) {
    const isDir = !content;
    const fileRecord = {
      path,
      content,
      isDir,
      timestamp: new Date(),
    };
    this.files.push(fileRecord);
  }

  addDirectory(dirPath, basePath = '') {
    const items = readdirSync(dirPath);
    for (const item of items) {
      const fullPath = join(dirPath, item);
      const relPath = join(basePath, item);
      const stats = statSync(fullPath);
      
      if (stats.isDirectory()) {
        this.addDirectory(fullPath, relPath);
      } else {
        const content = readFileSync(fullPath);
        this.addFile(relPath.replace(/\\/g, '/'), content);
      }
    }
  }

  toBuffer() {
    const buffers = [];
    
    for (const file of this.files) {
      const localHeader = this.createLocalFileHeader(file);
      buffers.push(localHeader);
      
      if (file.content) {
        buffers.push(file.content);
      }
      
      const centralDirEntry = this.createCentralDirectoryEntry(file, this.offset);
      this.centralDirectory.push(centralDirEntry);
      
      this.offset += localHeader.length + (file.content ? file.content.length : 0);
    }
    
    const centralDirStart = this.offset;
    for (const entry of this.centralDirectory) {
      buffers.push(entry);
      this.offset += entry.length;
    }
    
    const endCentralDir = this.createEndOfCentralDirectory(
      this.files.length,
      centralDirStart,
      this.offset - centralDirStart
    );
    buffers.push(endCentralDir);
    
    return Buffer.concat(buffers);
  }

  createLocalFileHeader(file) {
    const pathBuf = Buffer.from(file.path, 'utf8');
    const timestamp = this.dosDateTime(file.timestamp);
    
    const buf = Buffer.alloc(30 + pathBuf.length);
    buf.writeUInt32LE(0x04034b50, 0); // Local file header signature
    buf.writeUInt16LE(10, 4); // Version needed to extract
    buf.writeUInt16LE(0, 6); // General purpose bit flag
    buf.writeUInt16LE(0, 8); // Compression method (0 = no compression)
    buf.writeUInt32LE(timestamp, 10); // Last mod file time and date
    buf.writeUInt32LE(0, 14); // CRC-32 (we'll leave as 0 for simplicity)
    buf.writeUInt32LE(file.content ? file.content.length : 0, 18); // Compressed size
    buf.writeUInt32LE(file.content ? file.content.length : 0, 22); // Uncompressed size
    buf.writeUInt16LE(pathBuf.length, 26); // File name length
    buf.writeUInt16LE(0, 28); // Extra field length
    pathBuf.copy(buf, 30);
    
    return buf;
  }

  createCentralDirectoryEntry(file, offset) {
    const pathBuf = Buffer.from(file.path, 'utf8');
    const timestamp = this.dosDateTime(file.timestamp);
    
    const buf = Buffer.alloc(46 + pathBuf.length);
    buf.writeUInt32LE(0x02014b50, 0); // Central file header signature
    buf.writeUInt16LE(10, 4); // Version made by
    buf.writeUInt16LE(10, 6); // Version needed to extract
    buf.writeUInt16LE(0, 8); // General purpose bit flag
    buf.writeUInt16LE(0, 10); // Compression method
    buf.writeUInt32LE(timestamp, 12); // Last mod file time and date
    buf.writeUInt32LE(0, 16); // CRC-32
    buf.writeUInt32LE(file.content ? file.content.length : 0, 20); // Compressed size
    buf.writeUInt32LE(file.content ? file.content.length : 0, 24); // Uncompressed size
    buf.writeUInt16LE(pathBuf.length, 28); // File name length
    buf.writeUInt16LE(0, 30); // Extra field length
    buf.writeUInt16LE(0, 32); // File comment length
    buf.writeUInt16LE(0, 34); // Disk number start
    buf.writeUInt16LE(0, 36); // Internal file attributes
    buf.writeUInt32LE(file.isDir ? 0x10 : 0, 38); // External file attributes
    buf.writeUInt32LE(offset, 42); // Relative offset of local header
    pathBuf.copy(buf, 46);
    
    return buf;
  }

  createEndOfCentralDirectory(count, offset, size) {
    const buf = Buffer.alloc(22);
    buf.writeUInt32LE(0x06054b50, 0); // End of central dir signature
    buf.writeUInt16LE(0, 4); // Number of this disk
    buf.writeUInt16LE(0, 6); // Number of the disk with the start of the central directory
    buf.writeUInt16LE(count, 8); // Total number of entries in the central dir on this disk
    buf.writeUInt16LE(count, 10); // Total number of entries in the central dir
    buf.writeUInt32LE(size, 12); // Size of the central directory
    buf.writeUInt32LE(offset, 16); // Offset of start of central directory
    buf.writeUInt16LE(0, 20); // ZIP file comment length
    
    return buf;
  }

  dosDateTime(date) {
    const d = date || new Date();
    const year = d.getFullYear() - 1980;
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const hours = d.getHours();
    const minutes = d.getMinutes();
    const seconds = Math.floor(d.getSeconds() / 2);
    
    return (year << 25) | (month << 21) | (day << 16) | (hours << 11) | (minutes << 5) | seconds;
  }
}

const zip = new SimpleZip();
zip.addDirectory(distPath);
const zipBuffer = zip.toBuffer();

const output = createWriteStream(join(outputPath, zipFileName));
output.write(zipBuffer);
output.end();

output.on('finish', () => {
  console.log(`\n✓ Build package created successfully!`);
  console.log(`  File: ${zipFileName}`);
  console.log(`  Size: ${(zipBuffer.length / 1024 / 1024).toFixed(2)} MB`);
});

output.on('error', (err) => {
  console.error('Error creating zip:', err);
  process.exit(1);
});
