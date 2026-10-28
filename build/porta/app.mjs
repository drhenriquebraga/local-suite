import { animate } from 'motion';
import { createBeamRenderer } from './beam-renderer.mjs';

const NS = 'http://www.w3.org/2000/svg';
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
const suite = document.querySelector('#suite');
const scene = document.querySelector('#scene');
const rig = document.querySelector('#art-rig');
const drift = document.querySelector('#art-drift');
const canvas = document.querySelector('#light-canvas');
const glassLayers = document.querySelector('#glass-layers');
const panels = [
  { x: 451, y: 314, rx: 78, ry: 107, shape: 'M354 209Q354 190 376 184L547 168Q565 166 566 188L566 418Q566 431 550 436L375 465Q354 469 354 448Z' },
  { x: 605, y: 332, rx: 75, ry: 112, shape: 'M508 225Q508 206 530 199L682 180Q701 178 703 201L703 434Q703 447 686 451L529 480Q508 486 508 464Z' },
  { x: 760, y: 348, rx: 75, ry: 114, shape: 'M655 244Q655 222 678 215L832 189Q852 188 853 211L853 454Q853 468 834 473L679 497Q656 502 655 480Z' },
  { x: 922, y: 365, rx: 72, ry: 114, shape: 'M827 266Q827 245 849 238L978 204Q999 198 1001 220L1001 468Q1001 485 982 490L850 525Q828 531 827 508Z' },
  { x: 1090, y: 385, rx: 76, ry: 116, shape: 'M999 286Q999 265 1021 255L1156 210Q1177 203 1179 225L1179 480Q1179 498 1159 505L1024 542Q1001 550 999 526Z' },
  { x: 1260, y: 402, rx: 72, ry: 116, shape: 'M1178 307Q1178 285 1200 274L1309 224Q1329 217 1331 241L1331 491Q1331 509 1311 517L1204 564Q1180 573 1178 549Z' }
];

function svgElement(tag, attributes = {}) {
  const element = document.createElementNS(NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}

function iniciar() {
  const cards = [...document.querySelectorAll('.tool-card')].slice(0, panels.length);
  const settings = { motion: true, intensity: 0.65 };
  let active = -1;
  let hovered = -1;
  let focused = -1;
  let pointerFrame = 0;
  let driftControl;
  let renderLights = () => {};
  const feedbackControls = new Map();
  const iconControls = new Map();
  const tiltControls = new Map();

  panels.forEach((panel, index) => {
    const group = svgElement('g', { class: 'ls-placa', 'data-glass': index });
    const halo = svgElement('ellipse', { cx: panel.x, cy: panel.y, rx: panel.rx * 1.35, ry: panel.ry * 1.15, fill: 'url(#pane-light)' });
    const edge = svgElement('path', { d: panel.shape, fill: '#8477ff', 'fill-opacity': '.018', stroke: '#f7dfb6', 'stroke-opacity': '.48', 'stroke-width': '1.25' });
    const ring = svgElement('ellipse', { class: 'ls-anel', cx: panel.x, cy: panel.y, rx: panel.rx * .53, ry: panel.ry * .62, fill: 'none', stroke: '#d3c5ff', 'stroke-width': '1.4', filter: 'url(#soft-light)' });
    const clip = svgElement('clipPath', { id: `ls-pane-${index}` });
    clip.append(svgElement('path', { d: panel.shape }));
    halo.setAttribute('clip-path', `url(#ls-pane-${index})`);
    ring.setAttribute('clip-path', `url(#ls-pane-${index})`);
    group.append(clip, halo, edge, ring);
    glassLayers.append(group);
  });
  const feedback = [...glassLayers.children];

  function nameOf(index) {
    const label = cards[index] && cards[index].querySelector('.tool-name');
    return label ? label.textContent.trim() : '';
  }
  function motionAllowed() { return settings.motion && !reduced.matches; }
  function stopControl(map, key) { map.get(key)?.stop(); map.delete(key); }
  function selectTool(index) {
    if (active === index) return;
    active = index;
    scene.dataset.activeTool = index < 0 ? '' : nameOf(index);
    cards.forEach((card, i) => {
      const selected = index === i;
      card.dataset.active = String(selected);
      stopControl(feedbackControls, i);
      stopControl(iconControls, i);
      const icon = card.querySelector('.tool-icon');
      const ring = feedback[i].querySelector('.ls-anel');
      ring.getAnimations().forEach(animation => animation.cancel());
      ring.style.opacity = '0';
      if (!motionAllowed() || hovered < 0) {
        feedback[i].style.opacity = selected ? '.72' : '0';
        if (icon) icon.style.transform = 'translateY(0px) rotate(0deg) scale(1)';
        return;
      }
      feedbackControls.set(i, animate(feedback[i], { opacity: selected ? .88 : 0 }, { duration: .2, ease: [.23, 1, .32, 1] }));
      const turn = [0, -2, 5, -1, -4, 2][i];
      if (icon) iconControls.set(i, animate(icon, { transform: selected ? `translateY(-2px) rotate(${turn}deg) scale(1.045)` : 'translateY(0px) rotate(0deg) scale(1)' }, { type: 'spring', duration: .5, bounce: .2 }));
      if (selected) {
        ring.animate([
          { opacity: 0, transform: 'scale(.96)' },
          { opacity: .7, transform: 'scale(1.08)', offset: .42 },
          { opacity: 0, transform: 'scale(1.25)' }
        ], { duration: 650, easing: 'ease-out' });
      }
    });
    renderLights();
  }

  function updateSelection() { selectTool(hovered >= 0 ? hovered : focused); }
  cards.forEach((card, index) => {
    card.addEventListener('pointerenter', event => {
      if (event.pointerType === 'touch' || !finePointer.matches) return;
      hovered = index;
      updateSelection();
    });
    card.addEventListener('pointerleave', () => {
      hovered = -1;
      card.style.setProperty('--mx', '50%');
      card.style.setProperty('--my', '20%');
      stopControl(tiltControls, index);
      if (motionAllowed()) tiltControls.set(index, animate(card, { transform: 'perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0px)' }, { type: 'spring', duration: .5, bounce: .2 }));
      else card.style.transform = 'none';
      updateSelection();
    });
    card.addEventListener('pointermove', event => {
      if (!finePointer.matches || !motionAllowed() || event.pointerType === 'touch') return;
      const rect = card.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
      const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
      card.style.setProperty('--mx', `${(x * 100).toFixed(1)}%`);
      card.style.setProperty('--my', `${(y * 100).toFixed(1)}%`);
      stopControl(tiltControls, index);
      tiltControls.set(index, animate(card, { transform: `perspective(900px) rotateX(${((.5 - y) * 3).toFixed(2)}deg) rotateY(${((x - .5) * 3).toFixed(2)}deg) translateY(-3px)` }, { type: 'spring', duration: .5, bounce: .2 }));
    });
    card.addEventListener('focus', () => { focused = index; updateSelection(); });
    card.addEventListener('blur', () => { focused = -1; updateSelection(); });
  });

  function fitArt() {
    const bounds = scene.getBoundingClientRect();
    const mobile = bounds.width <= 800;
    const heroFraction = mobile ? .35 : .49;
    const scale = Math.min(bounds.width * (mobile ? 1.5 : 1) / 1672, bounds.height * heroFraction / 460);
    rig.style.width = `${1672 * scale}px`;
    rig.style.height = `${941 * scale}px`;
    rig.style.top = `${bounds.height * (.16 + heroFraction / 2) - 380 * scale}px`;
    renderLights();
  }
  drift.style.transform = 'translate(0px,0px)';
  new ResizeObserver(fitArt).observe(scene);
  fitArt();

  suite.addEventListener('pointermove', event => {
    if (!finePointer.matches || !motionAllowed() || event.pointerType === 'touch') return;
    cancelAnimationFrame(pointerFrame);
    pointerFrame = requestAnimationFrame(() => {
      const x = (event.clientX / innerWidth - .5) * 5;
      const y = (event.clientY / innerHeight - .5) * 3;
      driftControl?.stop();
      driftControl = animate(drift, { transform: `translate(${x.toFixed(2)}px,${y.toFixed(2)}px)` }, { type: 'spring', duration: .5, bounce: .2 });
    });
  });
  suite.addEventListener('pointerleave', () => {
    driftControl?.stop();
    if (motionAllowed()) driftControl = animate(drift, { transform: 'translate(0px,0px)' }, { type: 'spring', duration: .5, bounce: .2 });
  });

  function applyMotionPreference() {
    if (!motionAllowed()) {
      driftControl?.stop();
      cancelAnimationFrame(pointerFrame);
      drift.style.transform = 'translate(0px,0px)';
      for (const [index] of tiltControls) stopControl(tiltControls, index);
      cards.forEach(card => { card.style.transform = 'none'; });
    }
    const selection = active;
    active = -2;
    selectTool(selection);
    renderLights();
  }
  reduced.addEventListener('change', applyMotionPreference);

  renderLights = createBeamRenderer({ canvas, scene, rig, panels, settings, getActive: () => active, motionAllowed, dialogs: [] });

  applyMotionPreference();
}

if (suite && scene && rig && drift && canvas && glassLayers) iniciar();
