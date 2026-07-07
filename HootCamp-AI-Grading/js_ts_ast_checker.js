#!/usr/bin/env node
// Simple JS/TS AST pattern scanner using @babel/parser + @babel/traverse
// Emits JSON with findings array.
// Install dependencies: npm install @babel/parser @babel/traverse

const fs = require('fs');
const path = require('path');
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;

function scanFile(filePath) {
  const code = fs.readFileSync(filePath, 'utf8');
  let ast;
  try {
    ast = parser.parse(code, { sourceType: 'module', plugins: ['typescript', 'jsx', 'classProperties', 'decorators-legacy']});
  } catch (e) {
    return [{file: filePath, line: 0, code: 'PARSE_ERROR', message: String(e)}];
  }
  const findings = [];
  traverse(ast, {
    CallExpression(pathNode) {
      const callee = pathNode.node.callee;
      if (callee.type === 'Identifier' && (callee.name === 'eval' || callee.name === 'Function')) {
        findings.push({file:filePath, line: pathNode.node.loc.start.line, code:'DANGEROUS_EVAL', message:'use of eval/new Function'});
      }
      if (callee.type === 'MemberExpression') {
        const obj = callee.object.name || '';
        const prop = callee.property.name || '';
        if (obj === 'child_process' && ['exec','execSync','spawn'].includes(prop)) {
          findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'SHELL_EXEC', message:`child_process.${prop} usage`});
        }
      }
    },
    ImportDeclaration(pathNode){
      const src = pathNode.node.source.value || '';
      if (/(openai|supabase|@supabase|axios|node-fetch)/i.test(src)) {
        findings.push({file:pathNode.node.source.value, line:pathNode.node.loc.start.line, code:'AI_OR_BACKEND_LIB', message:`import ${src}`});
      }
    },
    Identifier(pathNode){
      if (pathNode.node.name === 'jwt' || pathNode.node.name === 'passport') {
        findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'AUTH_HINT', message:`auth library identifier ${pathNode.node.name}`});
      }
    }
  });
  return findings;
}

function walkDir(dir) {
  const results = [];
  const items = fs.readdirSync(dir);
  for (const name of items) {
    const p = path.join(dir, name);
    const stat = fs.statSync(p);
    if (stat.isDirectory()) {
      results.push(...walkDir(p));
    } else if (/\.(js|ts|jsx|tsx)$/.test(p)) {
      results.push(...scanFile(p));
    }
  }
  return results;
}

const target = process.argv[2] || '.';
const stats = walkDir(target);
console.log(JSON.stringify({repo: path.basename(target), findings: stats}, null, 2));
