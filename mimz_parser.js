// mimz_parser.js — v1.0
// Parses 132-byte nest from PNG tEXt chunk
// Usage: const core = await Mimz.parsePNG(file)

export const Mimz = {
  SIGNATURE: "))))))))(((((((( -1 -i 0 0 1 i 0 0 ))))))))(((((((( =1",
  
  async parsePNG(fileOrBlob) {
    const buf = await fileOrBlob.arrayBuffer();
    const bytes = new Uint8Array(buf);
    
    // Verify PNG signature
    if (bytes[0] !== 0x89 || bytes[1] !== 0x50) throw new Error('Not a PNG');
    
    let offset = 8;
    let mimzData = null;
    
    while (offset < bytes.length) {
      const length = (bytes[offset]<<24) | (bytes[offset+1]<<16) | (bytes[offset+2]<<8) | bytes[offset+3];
      const type = String.fromCharCode(...bytes.slice(offset+4, offset+8));
      
      if (type === 'tEXt') {
        const data = bytes.slice(offset+8, offset+8+length);
        const text = new TextDecoder().decode(data);
        const [key, ...rest] = text.split('\0');
        if (key === 'mimz') {
          const b64 = rest.join('\0');
          mimzData = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
          break;
        }
      }
      offset += 12 + length;
    }
    
    if (!mimzData || mimzData.length !== 132) throw new Error('No mimz nest found');
    
    return this.parseNest(mimzData);
  },
  
  parseNest(nest) {
    const view = new DataView(nest.buffer);
    const sig = new TextDecoder().decode(nest.slice(0,64)).replace(/\0+$/, '');
    
    return {
      signature: sig,
      magic: String.fromCharCode(...nest.slice(64,68)),
      version: nest[68],
      planes: nest[69],
      per_plane: nest[70],
      dipoles: nest[71],
      nodes: nest[72],
      core_bit: nest[73],
      vector: Array.from(nest.slice(74,82)).map(b => b > 127 ? b-256 : b),
      sha256: Array.from(nest.slice(82,114)).map(b => b.toString(16).padStart(2,'0')).join(''),
      timestamp: Number(view.getBigUint64(114)),
      creation_hash: Array.from(nest.slice(122,132)).map(b => b.toString(16).padStart(2,'0')).join(''),
      equals: 1,
      equation: 'x2 mirrored = 4 = 1 mirrored x3 = 1',
      valid: sig.trim() === this.SIGNATURE
    };
  },
  
  async verify(core) {
    const data = core.signature + core.timestamp;
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(data));
    const hex = Array.from(new Uint8Array(hash)).map(b=>b.toString(16).padStart(2,'0')).join('');
    return hex.startsWith(core.sha256.slice(0,16)); // partial verify
  },
  
  // Rebuild toroid geometry from core
  buildGeometry(core) {
    const phi = (1 + Math.sqrt(5)) / 2;
    return {
      planes: core.planes,
      perPlane: core.per_plane,
      dipoles: core.dipoles,
      vector: core.vector,
      coreBit: core.core_bit,
      // Returns 10×3 control points
      controlPoints: Array.from({length: core.planes}, (_, i) => 
        Array.from({length: core.per_plane}, (_, j) => ({
          x: Math.cos(i * Math.PI / 5) * phi,
          y: Math.sin(i * Math.PI / 5) * phi,
          z: (j - 1) * 0.5,
          phase: core.vector[i % 8]
        }))
      )
    };
  }
};
