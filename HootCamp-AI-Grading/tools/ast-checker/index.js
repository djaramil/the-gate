const fs = require('fs');
const glob = require('glob');
const parser = require('@babel/parser');

function parseFile(filePath){
  const code = fs.readFileSync(filePath, 'utf8');
  return parser.parse(code, { sourceType: 'module', plugins: ['typescript', 'jsx'] });
}

try {
  const files = glob.sync('**/*.{js,ts,jsx,tsx}', { ignore: ['**/node_modules/**'] });
  files.forEach(f => {
    try {
      parseFile(f);
      console.log('OK', f);
    } catch (e) {
      console.error('ERR', f, e.message);
    }
  });
} catch (err) {
  console.error(err);
  process.exit(1);
}
