/**
 * Utility functions for the streaming chat interface
 */

/**
 * Formats JSON-LD data as colored HTML for display
 * 
 * @param {Object|string} jsonLd - The JSON-LD data to format
 * @returns {string} - HTML representation of the JSON-LD
 */
export function jsonLdToHtml(jsonLd) {
  // Helper function to escape HTML special characters
  const escapeHtml = (str) => {
    if (typeof str !== 'string') return '';
    
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  // Helper function to format a single value
  const formatValue = (value, indent) => {
    const spaces = '  '.repeat(indent);
    
    if (value === null) {
      return `<span class="null">null</span>`;
    }
    
    switch (typeof value) {
      case 'string':
        // Special handling for URLs and IRIs in JSON-LD
        if (value.startsWith('http://') || value.startsWith('https://')) {
          return `<span class="string url">"${escapeHtml(value)}"</span>`;
        }
        return `<span class="string">"${escapeHtml(value)}"</span>`;
      case 'number':
        return `<span class="number">${value}</span>`;
      case 'boolean':
        return `<span class="boolean">${value}</span>`;
      case 'object':
        if (Array.isArray(value)) {
          if (value.length === 0) return '[]';
          const items = value.map(item => 
            `${spaces}  ${formatValue(item, indent + 1)}`
          ).join(',\n');
          return `[\n${items}\n${spaces}]`;
        }
        return formatObject(value, indent);
      default:
        return `<span class="unknown">${escapeHtml(String(value))}</span>`;
    }
  };

  // Helper function to format an object
  const formatObject = (obj, indent = 0) => {
    const spaces = '  '.repeat(indent);
    
    if (!obj || Object.keys(obj).length === 0) return '{}';
    
    const entries = Object.entries(obj).map(([key, value]) => {
      // Special handling for JSON-LD keywords (starting with @)
      const keySpan = key.startsWith('@') 
        ? `<span class="keyword">"${escapeHtml(key)}"</span>`
        : `<span class="key">"${escapeHtml(key)}"</span>`;
        
      return `${spaces}  ${keySpan}: ${formatValue(value, indent + 1)}`;
    });
    
    return `{\n${entries.join(',\n')}\n${spaces}}`;
  };

  // Main formatting logic
  try {
    const parsed = (typeof jsonLd === 'string') ? JSON.parse(jsonLd) : jsonLd;
    const formatted = formatObject(parsed);
    
    // Return complete HTML with styling
    return `<pre class="json-ld"><code>${formatted}</code></pre>
<style>
.json-ld {
  background-color: #f5f5f5;
  padding: 1em;
  border-radius: 4px;
  font-family: monospace;
  line-height: 1.5;
}
.json-ld .keyword { color: #e91e63; }
.json-ld .key { color: #2196f3; }
.json-ld .string { color: #4caf50; }
.json-ld .string.url { color: #9c27b0; }
.json-ld .number { color: #ff5722; }
.json-ld .boolean { color: #ff9800; }
.json-ld .null { color: #795548; }
.json-ld .unknown { color: #607d8b; }
</style>`;
  } catch (error) {
    return `<pre class="json-ld error">Error: ${error.message}</pre>`;
  }
}

/**
 * Creates a random ID
 * 
 * @param {number} length - The length of the ID
 * @returns {string} - The random ID
 */
export function createRandomId(length = 8) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  
  return result;
}

/**
 * Debounces a function
 * 
 * @param {Function} func - The function to debounce
 * @param {number} wait - The debounce wait time
 * @returns {Function} - The debounced function
 */
export function debounce(func, wait) {
  let timeout;
  
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    
    timeout = setTimeout(() => {
      func.apply(context, args);
    }, wait);
  };
}

/**
 * Throttles a function
 * 
 * @param {Function} func - The function to throttle
 * @param {number} limit - The throttle limit time
 * @returns {Function} - The throttled function
 */
export function throttle(func, limit) {
  let inThrottle;
  
  return function(...args) {
    const context = this;
    
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}