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
      
      // Security: dangerous eval/Function
      if (callee.type === 'Identifier' && (callee.name === 'eval' || callee.name === 'Function')) {
        findings.push({file:filePath, line: pathNode.node.loc.start.line, code:'DANGEROUS_EVAL', message:'use of eval/new Function'});
      }
      
      // Security: child_process usage
      if (callee.type === 'MemberExpression') {
        const obj = callee.object.name || '';
        const prop = callee.property.name || '';
        if (obj === 'child_process' && ['exec','execSync','spawn'].includes(prop)) {
          findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'SHELL_EXEC', message:`child_process.${prop} usage`});
        }
      }
      
      // Supabase: createClient
      if (callee.type === 'Identifier' && callee.name === 'createClient') {
        findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'SUPABASE_CLIENT', message:'Supabase createClient call'});
      }
      
      // Supabase auth patterns
      if (callee.type === 'MemberExpression') {
        const obj = callee.object.name || '';
        const prop = callee.property.name || '';
        if (obj === 'supabase' || obj === 'auth') {
          if (['signInWithPassword', 'signUp', 'signOut', 'signInWithOAuth'].includes(prop)) {
            findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'SUPABASE_AUTH', message:`Supabase auth: ${prop}`});
          }
        }
      }
      
      // Supabase CRUD patterns
      if (callee.type === 'MemberExpression') {
        const obj = callee.object.name || '';
        const prop = callee.property.name || '';
        if (obj === 'supabase' && ['from', 'insert', 'select', 'update', 'delete'].includes(prop)) {
          findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'SUPABASE_CRUD', message:`Supabase CRUD: ${prop}`});
        }
      }
      
      // Check for require() calls (CommonJS)
      if (callee.type === 'Identifier' && callee.name === 'require' && pathNode.node.arguments.length > 0) {
        const arg = pathNode.node.arguments[0];
        if (arg.type === 'StringLiteral') {
          const src = arg.value;
          // AI/backend libraries via require
          if (/(openai|@google\/generative-ai|@supabase|supabase|axios|node-fetch|gemini)/i.test(src)) {
            findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'AI_OR_BACKEND_LIB', message:`require ${src}`});
          }
          // Auth libraries via require
          if (/(jsonwebtoken|passport|@auth|next-auth)/i.test(src)) {
            findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'AUTH_LIB', message:`auth library require ${src}`});
          }
        }
      }
    },
    ImportDeclaration(pathNode){
      const src = pathNode.node.source.value || '';
      
      // AI/backend libraries
      if (/(openai|@google\/generative-ai|@supabase|supabase|axios|node-fetch|gemini)/i.test(src)) {
        findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'AI_OR_BACKEND_LIB', message:`import ${src}`});
      }
      
      // Auth libraries
      if (/(jsonwebtoken|passport|@auth|next-auth)/i.test(src)) {
        findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'AUTH_LIB', message:`auth library import ${src}`});
      }
    },
    Identifier(pathNode){
      // Auth identifiers
      if (['jwt', 'passport', 'signIn', 'signUp', 'signOut', 'login', 'register'].includes(pathNode.node.name)) {
        findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'AUTH_HINT', message:`auth identifier ${pathNode.node.name}`});
      }
      
      // Supabase identifiers
      if (['supabase', 'createClient'].includes(pathNode.node.name)) {
        findings.push({file:filePath, line:pathNode.node.loc.start.line, code:'SUPABASE_HINT', message:`Supabase identifier ${pathNode.node.name}`});
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
