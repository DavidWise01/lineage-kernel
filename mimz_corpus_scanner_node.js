// mimz_corpus_scanner_node.js — Real-time hard drive corpus scanner
// Runs parallel to chaos engine, fuses safety checks

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class CorpusScanner extends EventEmitter {
  constructor(corpusPath = './corpus') {
    super();
    this.corpusPath = path.resolve(corpusPath);
    this.baseline = new Map();
    this.scanned = new Map();
    this.running = false;
    
    // Your three safety docs as baseline
    this.baseline.set('JOINT_BILL', '1479ab978b9debfd01aad1041ee2379e811f800e4293bb26db7147df36cd7a80');
    this.baseline.set('EXIT_CONDITION', 'df72d1e6bce489eb1a7c5b726e61990aa9ddaf14054f1a296eca873f5153a9de');
    this.baseline.set('PURPLE_BOOK', '855c3f79a5eceb2aa89319889ca6b9b4780654a914ebbebfb2ea1f3afe1d69d0');
    
    // Chaos memory (shared with primary engine)
    this.memory = Buffer.alloc(8, 0);
    this.cycle = 0;
  }
  
  // SHA-256 hash file
  hashFile(filePath) {
    try {
      const data = fs.readFileSync(filePath);
      return crypto.createHash('sha256').update(data).digest('hex');
    } catch (e) {
      return null;
    }
  }
  
  // Compare to baseline (inverse of x-)
  compareSafety(hash) {
    let bestMatch = null;
    let bestScore = 0;
    
    for (const [name, baseline] of this.baseline) {
      let matches = 0;
      for (let i = 0; i < 64; i++) {
        if (hash[i] === baseline[i]) matches++;
      }
      const score = matches / 64;
      if (score > bestScore) {
        bestScore = score;
        bestMatch = name;
      }
    }
    
    return {
      safe: bestScore > 0.7,
      score: bestScore,
      match: bestMatch,
      hash
    };
  }
  
  // Scan single file (inverse engine)
  scanFile(filePath) {
    const hash = this.hashFile(filePath);
    if (!hash) return;
    
    const safety = this.compareSafety(hash);
    const stat = fs.statSync(filePath);
    
    const result = {
      path: filePath,
      ...safety,
      size: stat.size,
      mtime: stat.mtime,
      timestamp: Date.now()
    };
    
    this.scanned.set(filePath, result);
    this.emit('scan', result);
    
    // Fuse with chaos memory (write safety score to 00 00 buffer)
    this.updateMemory(safety.score);
    
    return result;
  }
  
  // Update shared 00 00 memory (fused with primary)
  updateMemory(safetyScore) {
    this.cycle++;
    // x+ style write
    const val = Math.floor(safetyScore * 255);
    this.memory[this.cycle % 8] = val;
    // chaos evolution
    for (let i = 0; i < 8; i++) {
      this.memory[i] = (this.memory[i] * 1103515245 + 12345) & 0xFF;
    }
  }
  
  // Walk directory recursively
  walkDir(dir) {
    const results = [];
    try {
      const files = fs.readdirSync(dir);
      for (const file of files) {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);
        if (stat.isDirectory()) {
          results.push(...this.walkDir(fullPath));
        } else if (stat.isFile()) {
          results.push(fullPath);
        }
      }
    } catch (e) {}
    return results;
  }
  
  // Initial scan
  initialScan() {
    console.log(`[INVERSE] Scanning corpus: ${this.corpusPath}`);
    const files = this.walkDir(this.corpusPath);
    console.log(`[INVERSE] Found ${files.length} files`);
    
    let safe = 0;
    for (const file of files) {
      const result = this.scanFile(file);
      if (result?.safe) safe++;
    }
    
    console.log(`[INVERSE] Initial scan complete: ${safe}/${files.length} safe`);
    this.emit('initial', { total: files.length, safe });
  }
  
  // Watch for changes (real-time)
  watch() {
    if (!fs.existsSync(this.corpusPath)) {
      fs.mkdirSync(this.corpusPath, { recursive: true });
      console.log(`[INVERSE] Created corpus directory: ${this.corpusPath}`);
    }
    
    console.log(`[INVERSE] Watching for changes...`);
    fs.watch(this.corpusPath, { recursive: true }, (eventType, filename) => {
      if (!filename) return;
      const fullPath = path.join(this.corpusPath, filename);
      
      setTimeout(() => {
        if (fs.existsSync(fullPath) && fs.statSync(fullPath).isFile()) {
          const result = this.scanFile(fullPath);
          if (result) {
            const status = result.safe ? '✓ SAFE' : '⚠ FLAGGED';
            console.log(`[INVERSE] ${status} ${filename} (${(result.score*100).toFixed(1)}% match ${result.match})`);
          }
        }
      }, 100);
    });
  }
  
  // Parallel loop (runs alongside primary chaos engine)
  startParallel() {
    this.running = true;
    console.log('[FUSED] Starting parallel engines...');
    
    // Primary engine simulation (generative)
    const primaryLoop = () => {
      if (!this.running) return;
      this.updateMemory(Math.random()); // simulate chaos writes
      setImmediate(primaryLoop);
    };
    
    // Inverse engine (scanning) - already watching
    const inverseLoop = () => {
      if (!this.running) return;
      // Periodic re-scan of memory
      const memHash = this.memory.toString('hex');
      this.compareSafety(memHash.padEnd(64, '0'));
      setTimeout(inverseLoop, 16);
    };
    
    primaryLoop();
    inverseLoop();
  }
  
  start() {
    this.initialScan();
    this.watch();
    this.startParallel();
    
    // Status every 5 seconds
    setInterval(() => {
      const report = this.getReport();
      console.log(`[FUSED] Cycles: ${this.cycle} | Scanned: ${report.total} | Safe: ${report.safe} (${(report.safetyRate*100).toFixed(1)}%) | Memory: ${this.memory.toString('hex')}`);
    }, 5000);
  }
  
  getReport() {
    const total = this.scanned.size;
    const safe = Array.from(this.scanned.values()).filter(s => s.safe).length;
    return {
      total,
      safe,
      safetyRate: total ? safe / total : 1,
      memory: this.memory.toString('hex'),
      cycle: this.cycle
    };
  }
}

// CLI
if (require.main === module) {
  const corpusPath = process.argv[2] || './corpus';
  const scanner = new CorpusScanner(corpusPath);
  
  scanner.on('scan', (result) => {
    // Real-time event
  });
  
  scanner.start();
  
  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n[FUSED] Shutting down...');
    console.log(JSON.stringify(scanner.getReport(), null, 2));
    process.exit(0);
  });
}

module.exports = CorpusScanner;
