#!/usr/bin/env node
/**
 * Downloads a Figma frame image to temp/<nodeId>.png (cached).
 * Prints the absolute image path to stdout — capture it in shell scripts.
 * All progress logs go to stderr.
 *
 * Usage:
 *   node .claude/skills/figma-frame-export/fetch-figma.mjs "<figma_url>"
 *
 * Requires: Node.js v18+
 */

import fs   from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR  = __dirname;
const TOKEN_PATH = path.join(SKILL_DIR, '..', '..', '..', '.secrets', 'figma.json');
const TEMP_DIR   = path.join(SKILL_DIR, 'temp');

function parseFigmaUrl(url) {
    const branchMatch = url.match(/\/design\/[^/]+\/branch\/([^/?]+)/);
    const fileKey = branchMatch
        ? branchMatch[1]
        : url.match(/\/design\/([^/?]+)/)?.[1];
    if (!fileKey) throw new Error(`Cannot extract fileKey from URL: ${url}`);

    const nodeId = url.match(/node-id=([^&]+)/)?.[1];
    if (!nodeId) throw new Error('URL must contain node-id. Select a specific frame in Figma and copy the link.');

    return { fileKey, nodeId: decodeURIComponent(nodeId) };
}

async function main() {
    if (process.argv.length !== 3) {
        process.stderr.write('Usage: node fetch-figma.mjs "<figma_url>"\n');
        process.exit(1);
    }

    const figmaUrl = process.argv[2];
    const { fileKey, nodeId } = parseFigmaUrl(figmaUrl);

    const safeNodeId = nodeId.replace(/[:/\\?*|"<>]/g, '-');
    const imagePath  = path.join(TEMP_DIR, `${safeNodeId}.png`);

    if (fs.existsSync(imagePath)) {
        process.stderr.write(`Cached: temp/${safeNodeId}.png\n`);
        process.stdout.write(imagePath + '\n');
        return;
    }

    const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf-8')).token.trim();
    process.stderr.write(`fileKey: ${fileKey}, nodeId: ${nodeId}\n`);

    const apiUrl = `https://api.figma.com/v1/images/${fileKey}?ids=${nodeId}&format=png&scale=2`;
    const apiRes = await fetch(apiUrl, { headers: { 'X-Figma-Token': token } });
    if (!apiRes.ok) throw new Error(`Figma API error: ${apiRes.status} ${await apiRes.text()}`);

    const apiJson  = await apiRes.json();
    const imageUrl = Object.values(apiJson.images)[0];
    process.stderr.write(`Image URL: ${imageUrl}\n`);

    const imgRes   = await fetch(imageUrl);
    if (!imgRes.ok) throw new Error(`Image download error: ${imgRes.status}`);
    const imgBytes = Buffer.from(await imgRes.arrayBuffer());

    fs.mkdirSync(TEMP_DIR, { recursive: true });
    fs.writeFileSync(imagePath, imgBytes);
    process.stderr.write(`Saved: temp/${safeNodeId}.png (${imgBytes.length.toLocaleString()} bytes)\n`);

    process.stdout.write(imagePath + '\n');
}

main().catch(err => {
    process.stderr.write(`Error: ${err.message}\n`);
    process.exit(1);
});
