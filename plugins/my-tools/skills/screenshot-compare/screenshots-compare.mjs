#!/usr/bin/env node
/**
 * Compares two local screenshots side-by-side in the browser.
 *
 * Usage:
 *   node .claude/skills/screenshot-compare/screenshots-compare.mjs <screenshot_a> <screenshot_b>
 *
 * Requires: Node.js v18+
 */

import fs   from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import net  from 'node:net';
import { exec }          from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR  = __dirname;

const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
};

function findFreePort() {
    return new Promise(resolve => {
        const srv = net.createServer();
        srv.listen(0, () => {
            const { port } = srv.address();
            srv.close(() => resolve(port));
        });
    });
}

function openBrowser(url) {
    const cmd =
        process.platform === 'win32'  ? `start "" "${url}"` :
        process.platform === 'darwin' ? `open "${url}"` :
                                        `xdg-open "${url}"`;
    exec(cmd);
}

function toUrlPath(filePath) {
    return (path.isAbsolute(filePath)
        ? path.relative(process.cwd(), filePath)
        : filePath).replace(/\\/g, '/');
}

async function main() {
    if (process.argv.length !== 4) {
        console.error('Usage: node screenshots-compare.mjs <screenshot_a> <screenshot_b>');
        process.exit(1);
    }

    const [pathA, pathB] = process.argv.slice(2);

    for (const p of [pathA, pathB]) {
        if (!fs.existsSync(p)) {
            console.error(`File not found: ${p}`);
            process.exit(1);
        }
    }

    console.log(`A: ${pathA}`);
    console.log(`B: ${pathB}`);

    const port = await findFreePort();

    const server = http.createServer((req, res) => {
        const urlPath  = req.url.split('?')[0];
        const filePath = path.join(process.cwd(), urlPath);
        const ext      = path.extname(filePath);

        fs.readFile(filePath, (err, data) => {
            if (err) { res.writeHead(404); res.end('Not found'); return; }
            res.writeHead(200, { 'Content-Type': MIME[ext] ?? 'application/octet-stream' });
            res.end(data);
        });
    });

    server.listen(port, () => {
        const skillPath = path.relative(process.cwd(), SKILL_DIR).replace(/\\/g, '/');
        const url = `http://localhost:${port}/${skillPath}/viewer/index.html`
            + `?device=/${toUrlPath(pathA)}&figma=/${toUrlPath(pathB)}`;
        console.log(`\nServing at: ${url}`);
        console.log('Press Ctrl+C to stop the server...');
        openBrowser(url);
    });

    process.on('SIGINT', () => {
        server.close();
        console.log('\nServer stopped.');
        process.exit(0);
    });
}

main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
});
