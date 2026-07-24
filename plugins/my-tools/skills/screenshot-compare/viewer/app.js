const OVERLAY_WIDTH = 480; // px — ширина для режима Overlay

// Shared image state
let gDeviceImg   = null;
let gFigmaImg    = null;
let diffOffsetY  = 0;
let overlayScale = 100;

// ── Tab switching ────────────────────────────────────────────────────────────

function switchTab(name) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    document.querySelectorAll('.tab-btn')[name === 'diff' ? 0 : 1].classList.add('active');
}

// ── Image utilities ──────────────────────────────────────────────────────────

function loadImage(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error(`Failed to load: ${url}`));
        img.src = url;
    });
}

function imageToCanvas(img) {
    const canvas = document.createElement('canvas');
    canvas.width  = img.width;
    canvas.height = img.height;
    canvas.getContext('2d').drawImage(img, 0, 0);
    return canvas;
}

function cropToCanvas(img, topPx, bottomPx) {
    const croppedHeight = img.height - topPx - bottomPx;
    const canvas = document.createElement('canvas');
    canvas.width  = img.width;
    canvas.height = croppedHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, topPx, img.width, croppedHeight, 0, 0, img.width, croppedHeight);
    return canvas;
}

function scaleCanvas(src, targetW, targetH) {
    const canvas = document.createElement('canvas');
    canvas.width  = targetW;
    canvas.height = targetH;
    canvas.getContext('2d').drawImage(src, 0, 0, targetW, targetH);
    return canvas;
}

function drawToCanvas(id, srcCanvas) {
    const el = document.getElementById(id);
    el.width  = srcCanvas.width;
    el.height = srcCanvas.height;
    el.getContext('2d').drawImage(srcCanvas, 0, 0);
}

// ── Diff mode ────────────────────────────────────────────────────────────────

// Compares two same-size canvases pixel by pixel (no threshold).
// Returns diff canvas and pixel counts.
function computeDiff(canvasA, canvasB) {
    const w = canvasA.width;
    const h = canvasA.height;
    const dataA = canvasA.getContext('2d').getImageData(0, 0, w, h).data;
    const dataB = canvasB.getContext('2d').getImageData(0, 0, w, h).data;

    const diffCanvas = document.createElement('canvas');
    diffCanvas.width  = w;
    diffCanvas.height = h;
    const diffCtx  = diffCanvas.getContext('2d');
    const diffImg  = diffCtx.createImageData(w, h);
    const diffData = diffImg.data;

    let diffCount = 0;
    for (let i = 0; i < dataA.length; i += 4) {
        const alphaA = dataA[i + 3];
        const alphaB = dataB[i + 3];
        const isDiff =
            (alphaA > 10 || alphaB > 10) && (
                dataA[i]     !== dataB[i]     ||
                dataA[i + 1] !== dataB[i + 1] ||
                dataA[i + 2] !== dataB[i + 2]
            );

        if (isDiff) {
            diffData[i]     = 255;
            diffData[i + 1] = 0;
            diffData[i + 2] = 0;
            diffData[i + 3] = 255;
            diffCount++;
        } else {
            diffData[i]     = dataA[i];
            diffData[i + 1] = dataA[i + 1];
            diffData[i + 2] = dataA[i + 2];
            diffData[i + 3] = 77;
        }
    }

    diffCtx.putImageData(diffImg, 0, 0);
    return { canvas: diffCanvas, diffCount, total: w * h };
}

// Shifts canvasSrc vertically by offsetY pixels (positive = down).
function shiftCanvas(canvasSrc, offsetY) {
    const canvas = document.createElement('canvas');
    canvas.width  = canvasSrc.width;
    canvas.height = canvasSrc.height;
    canvas.getContext('2d').drawImage(canvasSrc, 0, offsetY);
    return canvas;
}

function setupDiff() {
    diffOffsetY = 0;

    // Full device screenshot without nav crop + figma scaled to match
    const deviceFull  = imageToCanvas(gDeviceImg);
    const figmaScaled = scaleCanvas(imageToCanvas(gFigmaImg), deviceFull.width, deviceFull.height);

    // At least 5% of device height must remain visible on either side
    const maxOffset = Math.round(deviceFull.height * 0.95);

    function redraw(offsetY) {
        const clamped       = Math.max(-maxOffset, Math.min(maxOffset, offsetY));
        diffOffsetY         = clamped;
        const deviceShifted = shiftCanvas(deviceFull, clamped);
        const { canvas: diffCanvas, diffCount, total } = computeDiff(deviceShifted, figmaScaled);

        drawToCanvas('device', deviceShifted);
        drawToCanvas('figma',  figmaScaled);
        drawToCanvas('diff',   diffCanvas);

        const pct   = ((diffCount / total) * 100).toFixed(2);
        const stats = document.getElementById('stats');
        stats.textContent = `Отличий: ${diffCount.toLocaleString()} px из ${total.toLocaleString()} (${pct}%)`;
        stats.classList.toggle('ok', parseFloat(pct) < 1);
    }

    redraw(0);

    // Drag to align device screenshot vertically
    const deviceCanvas = document.getElementById('device');
    deviceCanvas.style.cursor = 'grab';

    let dragging = false, startY = 0, startOffset = 0;

    deviceCanvas.addEventListener('mousedown', e => {
        dragging    = true;
        startY      = e.clientY;
        startOffset = diffOffsetY;
        deviceCanvas.style.cursor = 'grabbing';
        e.preventDefault();
    });

    window.addEventListener('mousemove', e => {
        if (!dragging) return;
        redraw(startOffset + (e.clientY - startY));
    });

    window.addEventListener('mouseup', () => {
        dragging = false;
        deviceCanvas.style.cursor = 'grab';
    });
}

// ── Overlay mode ─────────────────────────────────────────────────────────────

function toggleDeviceLayer() {
    const layer  = document.getElementById('device-layer');
    const btn    = document.getElementById('device-toggle');
    const slider = document.getElementById('opacity-slider');
    const isOn   = btn.classList.toggle('active');
    btn.textContent       = isOn ? 'Устройство: вкл' : 'Устройство: выкл';
    layer.style.opacity   = isOn ? slider.value / 100 : 0;
}

function onOpacityChange(value) {
    document.getElementById('opacity-val').textContent = value;
    const isOn = document.getElementById('device-toggle').classList.contains('active');
    if (isOn) document.getElementById('device-layer').style.opacity = value / 100;
}

function changeScale(delta) {
    overlayScale = Math.max(25, overlayScale + delta);
    document.getElementById('scale-val').textContent = overlayScale + '%';
    document.getElementById('overlay-scale-wrap').style.transform =
        `scale(${overlayScale / 100})`;
}

function setupOverlay() {
    const figmaScale = OVERLAY_WIDTH / gFigmaImg.width;
    const figmaH     = Math.round(gFigmaImg.height * figmaScale);
    const deviceH    = Math.round(gDeviceImg.height * (OVERLAY_WIDTH / gDeviceImg.width));

    const figmaLayer = document.getElementById('figma-layer');
    figmaLayer.width  = OVERLAY_WIDTH;
    figmaLayer.height = figmaH;
    figmaLayer.getContext('2d').drawImage(gFigmaImg, 0, 0, OVERLAY_WIDTH, figmaH);

    const deviceLayer = document.getElementById('device-layer');
    deviceLayer.width  = OVERLAY_WIDTH;
    deviceLayer.height = deviceH;
    deviceLayer.getContext('2d').drawImage(gDeviceImg, 0, 0, OVERLAY_WIDTH, deviceH);
    deviceLayer.style.opacity = '0.5';

    const wrapper = document.getElementById('overlay-wrapper');
    wrapper.style.width  = OVERLAY_WIDTH + 'px';
    wrapper.style.height = figmaH + 'px';

    let dragging = false, startY = 0, startTop = 0, currentTop = 0;

    wrapper.addEventListener('mousedown', e => {
        dragging = true;
        startY   = e.clientY;
        startTop = currentTop;
        e.preventDefault();
    });

    window.addEventListener('mousemove', e => {
        if (!dragging) return;
        const delta = (e.clientY - startY) / (overlayScale / 100);
        currentTop  = startTop + delta;
        deviceLayer.style.top = currentTop + 'px';
    });

    window.addEventListener('mouseup', () => { dragging = false; });
}

// ── Entry point ──────────────────────────────────────────────────────────────

async function main() {
    try {
        const params = new URLSearchParams(location.search);
        [gDeviceImg, gFigmaImg] = await Promise.all([
            loadImage(params.get('device')),
            loadImage(params.get('figma')),
        ]);

        setupDiff();
        setupOverlay();
    } catch (e) {
        document.getElementById('stats').textContent = 'Ошибка: ' + (e?.message ?? String(e));
    }
}

main();