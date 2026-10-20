// The glass plate is static artwork. Every ray and each optical surface below
// has independent geometry computed every frame; no light is baked into it.
export function createBeamRenderer({ canvas, scene, rig, panels, settings, getActive, motionAllowed, dialogs }) {
  const ctx = canvas.getContext('2d', { alpha: true, desynchronized: true });
  if (!ctx) { scene.dataset.renderer = 'static'; return () => {}; }
  const glow = document.createElement('canvas');
  glow.className = 'beam-bloom';
  glow.setAttribute('aria-hidden', 'true');
  canvas.before(glow);
  glow.width = 557;
  glow.height = 314;
  const bloom = glow.getContext('2d', { alpha: true });
  const clips = panels.map(panel => new Path2D(panel.shape));
  const colors = ['#33b9ff', '#5e86ff', '#9475ff', '#c9b6ff', '#88d7ff'];
  const TAU = Math.PI * 2;
  const smooth = (a, b, x) => { const v = Math.max(0, Math.min(1, (x - a) / (b - a))); return v * v * (3 - 2 * v); };
  let animationFrame = 0;
  let previous = 0;
  let time = 0;
  let ticks = 0;
  let width = 0;
  let height = 0;
  const canRun = () => motionAllowed() && !document.hidden && !dialogs.some(dialog => dialog.open);

  function rayY(x, strand, t) {
    const spread = strand / 35 - .5;
    const incoming = 1 - smooth(80, 410, x);
    const outgoing = smooth(1280, 1620, x);
    const axis = 261 + x * .113;
    const parallel = 20 * Math.sin((x - 1280) * .016 - t * .9)
      + 11 * Math.sin((x - 1280) * .028 - t * .65 + .7);
    // Shared outgoing displacement keeps all rays along one inclined volume.
    let y = axis + spread * (37 + incoming * 216 + outgoing * 52) * (1 + .11 * Math.sin(strand * 2.17));
    y += incoming * (54 * Math.sin(x * .011 - t * .8 + strand * .28) + 17 * Math.sin(x * .026 + t * .45 + strand * .36));
    y += outgoing * parallel;
    y += 5 * Math.sin(x * .024 - t * .8) * (1 - incoming) * (1 - outgoing);
    return y;
  }

  function rayPath(strand, t) {
    const path = new Path2D();
    for (let step = 0; step <= 140; step++) {
      const x = -20 + step * (1710 / 140);
      const y = rayY(x, strand, t);
      if (step) path.lineTo(x, y); else path.moveTo(x, y);
    }
    return path;
  }

  function opticalPath(panel, index, layer, t) {
    const radius = .18 + layer / 17 * .76;
    const phase = t * (.7 + index * .085) + index * 1.27;
    const path = new Path2D();
    for (let step = 0; step <= 64; step++) {
      const angle = step / 64 * TAU;
      const fold = 1 + .17 * Math.sin(angle * 3 + phase) + .085 * Math.cos(angle * 5 - phase * .71);
      const x = panel.x + Math.cos(angle) * panel.rx * .74 * radius * fold
        + Math.sin(angle * 2 + phase) * 7 * radius;
      const y = panel.y + Math.sin(angle) * panel.ry * .79 * radius * fold
        + Math.cos(angle * 3 - phase) * 13 * radius;
      if (step) path.lineTo(x, y); else path.moveTo(x, y);
    }
    path.closePath();
    return path;
  }

  function resize() {
    const bounds = rig.getBoundingClientRect();
    // Glow uses a separate small texture blurred by the compositor. Cap the
    // hidden off-screen portion of the mobile artwork instead of oversampling.
    const resolution = Math.min(devicePixelRatio || 1, 1, 1280 / bounds.width);
    const nextWidth = Math.max(1, Math.round(bounds.width * resolution));
    const nextHeight = Math.max(1, Math.round(bounds.height * resolution));
    if (width !== nextWidth || height !== nextHeight) {
      width = canvas.width = nextWidth;
      height = canvas.height = nextHeight;
    }
  }

  function revealGlassDepth(context) {
    // Remove only light behind the left face of each preserved glass. The
    // attenuation ends at its aperture center; the outgoing wave stays intact.
    context.save();
    context.globalCompositeOperation = 'destination-out';
    context.globalAlpha = 1;
    panels.forEach((panel, index) => {
      const left = panel.x - panel.rx * 1.4;
      const top = panel.y - panel.ry * 1.7;
      const mask = context.createLinearGradient(left, 0, panel.x, 0);
      mask.addColorStop(0, 'rgba(0,0,0,.78)');
      mask.addColorStop(.38, 'rgba(0,0,0,.70)');
      mask.addColorStop(.73, 'rgba(0,0,0,.32)');
      mask.addColorStop(1, 'rgba(0,0,0,0)');
      context.save();
      context.clip(clips[index]);
      context.fillStyle = mask;
      context.fillRect(left, top, panel.x - left, panel.ry * 3.4);
      context.restore();
    });
    context.restore();
  }

  function draw() {
    const drawStarted = performance.now();
    resize();
    ctx.setTransform(width / 1672, 0, 0, height / 941, 0, 0);
    ctx.clearRect(0, 0, 1672, 941);
    ctx.globalCompositeOperation = 'lighter';
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    bloom.setTransform(glow.width / 1672, 0, 0, glow.height / 941, 0, 0);
    bloom.clearRect(0, 0, 1672, 941);
    bloom.globalCompositeOperation = 'lighter';
    bloom.lineCap = 'round';
    const rays = Array.from({ length: 36 }, (_, strand) => rayPath(strand, time));
    const brightness = .8 + settings.intensity * .65;
    for (let strand = 0; strand < rays.length; strand++) {
      const color = colors[strand % colors.length];
      ctx.strokeStyle = bloom.strokeStyle = color;
      ctx.globalAlpha = brightness * (.43 + .18 * (.5 + .5 * Math.sin(time * 1.2 - strand * .7)));
      ctx.lineWidth = strand % 7 ? 1.15 : 2.1;
      ctx.stroke(rays[strand]);
      bloom.globalAlpha = .22 * brightness;
      bloom.lineWidth = strand % 7 ? 4 : 9;
      bloom.stroke(rays[strand]);
    }

    const active = getActive();
    panels.forEach((panel, index) => {
      ctx.save();
      ctx.clip(clips[index]);
      const selected = index === active;
      const phase = time * (.7 + index * .085) + index * 1.27;
      // Translucent surfaces have depth, with distinct phase and folds per glass.
      for (let layer = 17; layer >= 0; layer--) {
        const path = opticalPath(panel, index, layer, time);
        ctx.strokeStyle = colors[(layer + index) % colors.length];
        ctx.lineWidth = layer % 5 ? 1.05 : 1.8;
        ctx.globalAlpha = brightness * (layer % 5 ? .56 : .88) * (selected ? 1.2 : 1);
        ctx.stroke(path);
        if (layer % 5 === 0) {
          ctx.fillStyle = index % 2 ? '#8d73ff' : '#258aff';
          ctx.globalAlpha = .035 * brightness;
          ctx.fill(path);
          bloom.strokeStyle = colors[(layer + index) % colors.length];
          bloom.globalAlpha = .20 * brightness * (selected ? 1.6 : 1);
          bloom.lineWidth = 8;
          bloom.stroke(path);
        }
      }
      const center = ctx.createRadialGradient(panel.x, panel.y, 0, panel.x, panel.y, panel.rx * .95);
      center.addColorStop(0, selected ? '#d9c7ff60' : '#a88aff24');
      center.addColorStop(.35, '#677eff12');
      center.addColorStop(1, '#308aff00');
      ctx.fillStyle = center;
      ctx.globalAlpha = brightness * (.8 + .2 * Math.sin(phase));
      ctx.fillRect(panel.x - panel.rx, panel.y - panel.ry, panel.rx * 2, panel.ry * 2);
      ctx.restore();
    });

    // A moving light packet is followed by a short luminous wake along a ray.
    for (let particle = 0; particle < 42; particle++) {
      const strand = particle % 36;
      const x = ((time * (68 + particle % 5 * 8) + particle * 137.71) % 1790) - 60;
      const y = rayY(x, strand, time);
      const fade = smooth(-30, 20, x) * (1 - smooth(1635, 1720, x));
      const trail = new Path2D();
      for (let step = 0; step <= 8; step++) {
        const px = x - 22 + step * 2.75;
        const py = rayY(px, strand, time);
        if (step) trail.lineTo(px, py); else trail.moveTo(px, py);
      }
      ctx.strokeStyle = '#bcdfff';
      ctx.globalAlpha = .7 * fade * brightness;
      ctx.lineWidth = 1.2;
      ctx.stroke(trail);
      ctx.fillStyle = '#e0eaff';
      ctx.globalAlpha = .85 * fade * brightness;
      ctx.beginPath();
      ctx.arc(x, y, particle % 8 ? 1 : 1.8, 0, TAU);
      ctx.fill();
      bloom.fillStyle = '#7b91ff';
      bloom.globalAlpha = .35 * fade;
      bloom.beginPath();
      bloom.arc(x, y, 5, 0, TAU);
      bloom.fill();
    }
    // Apply the same local depth to rays, particles, optical surfaces and glow,
    // so the bloom cannot visually put the hidden wave in front of the glass.
    revealGlassDepth(ctx);
    revealGlassDepth(bloom);
    ctx.globalAlpha = 1;
    scene.dataset.beamTick = String(++ticks);
    scene.dataset.beamSample = rayY(1490, 12, time).toFixed(3);
    scene.dataset.opticalPhase = time.toFixed(3);
    scene.dataset.drawMs = (performance.now() - drawStarted).toFixed(1);
    scene.dataset.motion = canRun() ? 'running' : 'paused';
  }

  function loop(now) {
    if (!canRun()) { animationFrame = 0; previous = 0; scene.dataset.motion = 'paused'; return; }
    if (!previous || now - previous >= 1000 / 30) {
      time += previous ? Math.min((now - previous) / 1000, .1) : 0;
      previous = now;
      draw();
    }
    animationFrame = requestAnimationFrame(loop);
  }

  function render() {
    draw();
    if (canRun() && !animationFrame) { previous = 0; animationFrame = requestAnimationFrame(loop); }
    if (!canRun() && animationFrame) { cancelAnimationFrame(animationFrame); animationFrame = 0; previous = 0; }
  }
  scene.dataset.renderer = 'canvas2d';
  document.addEventListener('visibilitychange', render);
  window.addEventListener('pagehide', () => { cancelAnimationFrame(animationFrame); animationFrame = 0; previous = 0; });
  window.addEventListener('pageshow', render);
  return render;
}
