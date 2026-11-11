"use client";
/**
 * Realistic, blinking 3D eye (Three.js) that opens the homepage.
 *
 * progress 0.00–0.30  eye looks around (follows the pointer, small saccades) and blinks naturally
 * progress 0.30–0.65  zoom towards the pupil; the pupil dilates and the retina becomes visible through it
 * progress 0.65–1.00  the iris fades away, leaving a circular fundus view with a scanning sweep
 *
 * Everything is procedurally generated (no photographs). Decorative only — not a patient image.
 */
import { useEffect, useRef } from "react";

type Props = {
  progress?: { current: number };
  className?: string;
  /** "hero": eye sits right of the text on wide screens; "panel": centred (e.g. login). */
  layout?: "hero" | "panel";
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const seg = (p: number, a: number, b: number) => clamp((p - a) / (b - a));
const ease = (t: number) => t * t * (3 - 2 * t);

function rng(seed: number) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------------------- procedural textures
function irisCanvas(): HTMLCanvasElement {
  const S = 1024, c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d")!;
  const R = S / 2, cx = R, cy = R, r = rng(7);
  const base = g.createRadialGradient(cx, cy, R * 0.28, cx, cy, R);
  base.addColorStop(0, "#3a2210");
  base.addColorStop(0.08, "#7a4a22");
  base.addColorStop(0.24, "#a8733a");
  base.addColorStop(0.36, "#7d4f26");
  base.addColorStop(0.62, "#5a3418");
  base.addColorStop(0.86, "#3b2211");
  base.addColorStop(0.95, "#1e120a");
  base.addColorStop(1, "#140c07");
  g.fillStyle = base;
  g.fillRect(0, 0, S, S);
  // radial stroma fibres
  for (let i = 0; i < 5200; i++) {
    const th = r() * Math.PI * 2;
    const r0 = R * (0.3 + r() * 0.15), r1 = R * (0.55 + r() * 0.43);
    const wob = (r() - 0.5) * 0.05;
    const light = r() < 0.55;
    g.strokeStyle = light ? `rgba(${200 + r() * 40},${140 + r() * 50},${70 + r() * 40},${0.08 + r() * 0.14})`
      : `rgba(${30 + r() * 20},${16 + r() * 10},${8},${0.1 + r() * 0.18})`;
    g.lineWidth = 0.6 + r() * 1.8;
    g.beginPath();
    g.moveTo(cx + Math.cos(th) * r0, cy + Math.sin(th) * r0);
    g.quadraticCurveTo(cx + Math.cos(th + wob) * (r0 + r1) / 2, cy + Math.sin(th + wob) * (r0 + r1) / 2, cx + Math.cos(th + wob * 2) * r1, cy + Math.sin(th + wob * 2) * r1);
    g.stroke();
  }
  // collarette (zig-zag ring)
  g.strokeStyle = "rgba(214,160,96,0.55)";
  g.lineWidth = 3;
  g.beginPath();
  for (let k = 0; k <= 180; k++) {
    const th = (k / 180) * Math.PI * 2;
    const rr = R * (0.47 + 0.035 * Math.sin(th * 23) + 0.02 * (r() - 0.5));
    k ? g.lineTo(cx + Math.cos(th) * rr, cy + Math.sin(th) * rr) : g.moveTo(cx + Math.cos(th) * rr, cy + Math.sin(th) * rr);
  }
  g.stroke();
  // crypts
  for (let i = 0; i < 46; i++) {
    const th = r() * Math.PI * 2, rr = R * (0.5 + r() * 0.32);
    g.save();
    g.translate(cx + Math.cos(th) * rr, cy + Math.sin(th) * rr);
    g.rotate(th);
    g.fillStyle = `rgba(22,12,6,${0.25 + r() * 0.3})`;
    g.beginPath();
    g.ellipse(0, 0, R * (0.03 + r() * 0.05), R * (0.008 + r() * 0.014), 0, 0, Math.PI * 2);
    g.fill();
    g.restore();
  }
  // contraction furrows near the limbus
  g.strokeStyle = "rgba(18,10,6,0.35)";
  for (let k = 0; k < 3; k++) {
    g.lineWidth = 1.2;
    g.beginPath();
    g.arc(cx, cy, R * (0.8 + k * 0.05), r() * 6, r() * 6 + 2.4);
    g.stroke();
  }
  // speckles
  for (let i = 0; i < 1600; i++) {
    const th = r() * Math.PI * 2, rr = R * (0.3 + r() * 0.65);
    g.fillStyle = r() < 0.5 ? `rgba(230,180,110,${r() * 0.18})` : `rgba(10,6,3,${r() * 0.2})`;
    g.fillRect(cx + Math.cos(th) * rr, cy + Math.sin(th) * rr, 1.5, 1.5);
  }
  // pupillary ruff
  g.strokeStyle = "rgba(25,14,8,0.9)";
  g.lineWidth = R * 0.03;
  g.beginPath(); g.arc(cx, cy, R * 0.3, 0, Math.PI * 2); g.stroke();
  return c;
}

function fundusCanvas(): HTMLCanvasElement {
  const S = 1024, c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d")!;
  const R = S / 2, r = rng(42);
  const bg = g.createRadialGradient(R * 0.95, R, R * 0.05, R, R, R);
  bg.addColorStop(0, "#e8854a");
  bg.addColorStop(0.5, "#cf5d2f");
  bg.addColorStop(0.85, "#9c3418");
  bg.addColorStop(1, "#4a1308");
  g.fillStyle = bg;
  g.fillRect(0, 0, S, S);
  // choroidal mottling
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = r() < 0.5 ? `rgba(255,170,110,${r() * 0.06})` : `rgba(90,20,8,${r() * 0.07})`;
    const x = r() * S, y = r() * S, s = 6 + r() * 26;
    g.beginPath(); g.ellipse(x, y, s, s * (0.5 + r() * 0.5), r() * 3, 0, Math.PI * 2); g.fill();
  }
  // macula and fovea
  const mx = R * 0.8, my = R * 1.02;
  const mac = g.createRadialGradient(mx, my, 0, mx, my, R * 0.22);
  mac.addColorStop(0, "rgba(70,18,8,0.55)"); mac.addColorStop(1, "rgba(70,18,8,0)");
  g.fillStyle = mac; g.beginPath(); g.arc(mx, my, R * 0.22, 0, Math.PI * 2); g.fill();
  g.fillStyle = "rgba(255,220,180,0.35)"; g.beginPath(); g.arc(mx, my, 3, 0, Math.PI * 2); g.fill();
  // optic disc
  const dx = R * 1.42, dy = R * 0.98;
  const disc = g.createRadialGradient(dx + 6, dy - 4, 4, dx, dy, R * 0.15);
  disc.addColorStop(0, "#fff4d6"); disc.addColorStop(0.35, "#ffd79a"); disc.addColorStop(0.75, "#f0a866"); disc.addColorStop(1, "rgba(232,133,74,0)");
  g.fillStyle = disc; g.beginPath(); g.arc(dx, dy, R * 0.15, 0, Math.PI * 2); g.fill();
  // vessels: recursive branching from the disc
  const vessel = (x: number, y: number, ang: number, w: number, len: number, col: string, depth: number, curve: number) => {
    let px = x, py = y, a = ang;
    g.strokeStyle = col; g.lineCap = "round";
    const steps = Math.floor(len / 8);
    for (let i = 0; i < steps; i++) {
      a += curve + (r() - 0.5) * 0.12;
      const nx = px + Math.cos(a) * 8, ny = py + Math.sin(a) * 8;
      g.lineWidth = Math.max(0.6, w * (1 - i / steps * 0.6));
      g.beginPath(); g.moveTo(px, py); g.lineTo(nx, ny); g.stroke();
      if (depth > 0 && r() < 0.035) vessel(nx, ny, a + (r() < 0.5 ? 0.7 : -0.7), w * 0.6, len * 0.45, col, depth - 1, (r() - 0.5) * 0.02);
      px = nx; py = ny;
      if (Math.hypot(px - R, py - R) > R * 0.97) break;
    }
  };
  const vein = "rgba(110,18,12,0.85)", art = "rgba(168,44,26,0.8)";
  // superior & inferior temporal arcades curve around the macula
  vessel(dx, dy - 10, Math.PI + 0.55, 9, 640, vein, 3, 0.0045);
  vessel(dx, dy - 4, Math.PI + 0.45, 6.5, 600, art, 3, 0.005);
  vessel(dx, dy + 10, Math.PI - 0.55, 9, 640, vein, 3, -0.0045);
  vessel(dx, dy + 4, Math.PI - 0.45, 6.5, 600, art, 3, -0.005);
  // nasal branches
  vessel(dx + 8, dy - 6, -0.6, 5, 260, vein, 2, 0.002);
  vessel(dx + 8, dy + 6, 0.6, 5, 260, art, 2, -0.002);
  vessel(dx + 10, dy, 0.05, 4, 220, vein, 1, 0);
  // field-of-view vignette
  const v = g.createRadialGradient(R, R, R * 0.7, R, R, R);
  v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,0.55)");
  g.fillStyle = v; g.fillRect(0, 0, S, S);
  return c;
}

function scleraCanvas(): HTMLCanvasElement {
  // equirectangular: v = 0 is the front pole (cornea), v = 0.5 the equator
  const W = 1024, H = 512, c = document.createElement("canvas");
  c.width = W; c.height = H;
  const g = c.getContext("2d")!, r = rng(99);
  const grad = g.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "#fffdfb"); grad.addColorStop(0.3, "#fbf6f1"); grad.addColorStop(0.47, "#f1e2db"); grad.addColorStop(1, "#dcbcb0");
  g.fillStyle = grad; g.fillRect(0, 0, W, H);
  for (let i = 0; i < 70; i++) { // fine conjunctival vessels running towards the limbus
    let x = r() * W, y = H * (0.42 + r() * 0.12), a = -Math.PI / 2 + (r() - 0.5) * 0.9;
    g.strokeStyle = `rgba(${170 + r() * 40},${40 + r() * 30},${40 + r() * 20},${0.15 + r() * 0.35})`;
    let w = 0.6 + r() * 1.4;
    for (let k = 0; k < 40; k++) {
      a += (r() - 0.5) * 0.5;
      const nx = x + Math.cos(a) * 4, ny = y + Math.sin(a) * 4;
      g.lineWidth = w; g.beginPath(); g.moveTo(x, y); g.lineTo(nx, ny); g.stroke();
      x = nx; y = ny; w *= 0.97;
      if (y < H * 0.24) break;
    }
  }
  return c;
}

function glintCanvas(): HTMLCanvasElement {
  const S = 256, c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d")!;
  g.filter = "blur(5px)";
  g.fillStyle = "rgba(255,255,255,0.55)";
  const pane = (x: number, y: number, w: number, h: number) => { g.beginPath(); g.roundRect(x, y, w, h, 6); g.fill(); };
  pane(78, 70, 58, 66);
  g.filter = "blur(1.5px)";
  g.fillStyle = "rgba(255,255,255,0.95)";
  g.beginPath(); g.arc(168, 160, 7, 0, Math.PI * 2); g.fill();
  return c;
}

const IRIS_VERT = /* glsl */ `
  varying vec2 vP;
  void main() { vP = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;
const IRIS_FRAG = /* glsl */ `
  uniform sampler2D uIris; uniform sampler2D uFundus;
  uniform float uPupil, uFundusMix, uIrisAlpha, uTime, uScan, uHeat;
  varying vec2 vP;
  vec3 heat(float t) { return clamp(vec3(1.5 - abs(4.0 * t - 3.0), 1.5 - abs(4.0 * t - 2.0), 1.5 - abs(4.0 * t - 1.0)), 0.0, 1.0); }
  void main() {
    float r = length(vP);
    if (r > 1.04) discard;
    float edge = 0.012;
    if (r < uPupil + edge) {
      vec2 q = vP / uPupil;                       // fundus seen through the pupil
      vec3 f = texture2D(uFundus, q * 0.5 + 0.5).rgb;
      float sweepY = mix(-1.15, 1.15, fract(uTime * 0.22));
      f += vec3(0.35, 0.95, 0.9) * exp(-abs(q.y - sweepY) * 55.0) * uScan;
      float h = exp(-dot(q - vec2(-0.12, 0.28), q - vec2(-0.12, 0.28)) * 18.0) * 0.9
              + exp(-dot(q - vec2(-0.4, -0.18), q - vec2(-0.4, -0.18)) * 26.0) * 0.7
              + exp(-dot(q - vec2(0.1, -0.35), q - vec2(0.1, -0.35)) * 30.0) * 0.55;
      f = mix(f, heat(clamp(h, 0.0, 1.0)), clamp(h, 0.0, 1.0) * 0.5 * uHeat);
      vec3 col = mix(vec3(0.015, 0.012, 0.012), f, uFundusMix);
      float a = 1.0 - smoothstep(uPupil - edge, uPupil + edge, r);
      // pupil disc is always opaque; outside it the iris takes over
      vec2 ang = normalize(vP + 1e-5);
      float tr = mix(0.3, 1.0, clamp((r - uPupil) / (1.0 - uPupil), 0.0, 1.0));
      vec3 iris = texture2D(uIris, 0.5 + 0.5 * tr * ang).rgb;
      vec3 c = mix(iris, col, a);
      float alpha = mix(uIrisAlpha, 1.0, a);
      gl_FragColor = vec4(c, alpha);
      return;
    }
    vec2 ang = normalize(vP);
    float tr = mix(0.3, 1.0, clamp((r - uPupil) / (1.0 - uPupil), 0.0, 1.0));
    vec3 iris = texture2D(uIris, 0.5 + 0.5 * tr * ang).rgb;
    iris *= 1.0 - 0.35 * smoothstep(0.1, 1.0, vP.y);   // shadow of the upper lid
    iris *= mix(1.0, 0.45, smoothstep(0.82, 1.0, r));  // darker limbal ring
    float limbus = smoothstep(1.04, 0.9, r);
    gl_FragColor = vec4(iris, uIrisAlpha * limbus);
  }
`;

export function EyeScene({ progress, className, layout = "hero" }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const el = host.current, ovMaybe = svg.current;
    if (!el || !ovMaybe) return;
    const ov: SVGSVGElement = ovMaybe;
    let disposed = false;
    let cleanup = () => {};

    import("three").then((THREE) => {
      if (disposed) return;
      let renderer: InstanceType<typeof THREE.WebGLRenderer>;
      try {
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      } catch {
        el.dataset.fallback = "1";
        return;
      }
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setClearColor(0x000000, 0);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      const canvas = renderer.domElement;
      canvas.style.width = "100%"; canvas.style.height = "100%"; canvas.style.display = "block";
      el.insertBefore(canvas, ov);
      const skin = document.createElement("canvas");
      skin.style.cssText = "position:absolute;inset:0;width:100%;height:100%;";
      el.insertBefore(skin, canvas);
      const sk = skin.getContext("2d")!;
      // fine skin texture tile
      const grain = document.createElement("canvas");
      grain.width = grain.height = 160;
      { const gg = grain.getContext("2d")!, r = rng(5);
        for (let i = 0; i < 2600; i++) { gg.fillStyle = r() < 0.5 ? `rgba(255,235,220,${r() * 0.16})` : `rgba(80,40,25,${r() * 0.14})`; gg.fillRect(r() * 160, r() * 160, 1 + r(), 1 + r()); } }
      const grainPat = sk.createPattern(grain, "repeat")!;
      // stable per-lash variation
      const lr = rng(31);
      const LASH = Array.from({ length: 78 }, (_, k) => ({ row: k % 2, t: 0.08 + (Math.floor(k / 2) / 38) * 0.88 + (lr() - 0.5) * 0.012,
        len: 0.75 + lr() * 0.5, ang: (lr() - 0.5) * 0.35, curl: 0.35 + lr() * 0.35, w: 0.7 + lr() * 0.6 }));
      const LOW = Array.from({ length: 26 }, () => ({ t: 0.18 + lr() * 0.7, len: 0.6 + lr() * 0.6, ang: (lr() - 0.5) * 0.3 }));

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 80);
      scene.add(new THREE.AmbientLight(0xffffff, 1.05));
      const key = new THREE.DirectionalLight(0xffffff, 1.6);
      key.position.set(-3, 4, 6);
      scene.add(key);
      const fill = new THREE.DirectionalLight(0xdbe8ff, 0.5);
      fill.position.set(4, -2, 3);
      scene.add(fill);

      const tex = (cv: HTMLCanvasElement) => { const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
      const irisTex = tex(irisCanvas()), fundusTex = tex(fundusCanvas()), scleraTex = tex(scleraCanvas()), glintTex = tex(glintCanvas());

      // eyeball: sphere with an opening for the iris (cornea pole at +Z)
      const Rb = 2.6, Ri = 1.0;
      const th0 = Math.asin(Ri / Rb);
      const zc = -Rb * Math.cos(th0);                 // sphere centre so the rim sits at z = 0
      const ball = new THREE.Group();
      ball.position.z = zc;
      scene.add(ball);
      const sGeo = new THREE.SphereGeometry(Rb, 96, 64, 0, Math.PI * 2, th0, Math.PI - th0);
      sGeo.rotateX(Math.PI / 2);
      const sMat = new THREE.MeshStandardMaterial({ map: scleraTex, roughness: 0.42, metalness: 0, transparent: true });
      ball.add(new THREE.Mesh(sGeo, sMat));
      const irisUniforms = {
        uIris: { value: irisTex }, uFundus: { value: fundusTex }, uPupil: { value: 0.33 }, uFundusMix: { value: 0 },
        uIrisAlpha: { value: 1 }, uTime: { value: 0 }, uScan: { value: 0 }, uHeat: { value: 0 },
      };
      const iMat = new THREE.ShaderMaterial({ vertexShader: IRIS_VERT, fragmentShader: IRIS_FRAG, uniforms: irisUniforms, transparent: true });
      const iGeo = new THREE.CircleGeometry(1.04, 128);
      const irisMesh = new THREE.Mesh(iGeo, iMat);
      irisMesh.position.z = -zc - 0.04;               // just behind the rim, inside the ball group
      ball.add(irisMesh);
      // corneal reflection stays fixed relative to the light (does not rotate with gaze)
      const gMat = new THREE.MeshBasicMaterial({ map: glintTex, transparent: true, depthWrite: false, opacity: 0.9 });
      const glint = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 0.95), gMat);
      glint.position.set(-0.2, 0.26, 0.3);
      scene.add(glint);

      // ---- layout & projection helpers
      let W = 1, H = 1, dRest = 8, dEnd = 3.2, cxFrac = 0.5, cyFrac = 0.5;
      const resize = () => {
        W = el.clientWidth; H = el.clientHeight;
        renderer.setSize(W, H, false);
        const dpr = Math.min(window.devicePixelRatio, 2);
        skin.width = Math.round(W * dpr); skin.height = Math.round(H * dpr);
        sk.setTransform(dpr, 0, 0, dpr, 0, 0);
        const aspect = W / Math.max(H, 1);
        const tanH = Math.tan(THREE.MathUtils.degToRad(19));
        const wide = layout === "hero" && W >= 1024;
        if (layout === "panel") { cxFrac = 0.5; cyFrac = 0.44; }
        else if (wide) { cxFrac = 0.7; cyFrac = 0.5; }
        else { cxFrac = 0.5; cyFrac = 0.7; }
        const fitW = wide ? 0.235 : layout === "panel" ? 0.4 : 0.44; // fraction of width the eye half-width may use
        dRest = Math.max(7.2, 2.75 / (tanH * aspect * fitW * 2));
        dEnd = Math.max(3.1, 0.98 / (tanH * Math.min(1, aspect) * (wide ? 0.82 : 0.86)));
        camera.aspect = aspect;
        // shift the eye to (cxFrac, cyFrac) of the viewport without moving it in 3D
        camera.setViewOffset(W, H, (0.5 - cxFrac) * W, (0.5 - cyFrac) * H, W, H);
        camera.updateProjectionMatrix();
      };
      resize();
      const ro = new ResizeObserver(resize);
      ro.observe(el);

      const pointer = { x: 0, y: 0 };
      const onMove = (e: PointerEvent) => {
        const b = el.getBoundingClientRect();
        pointer.x = clamp(((e.clientX - b.left) / b.width - cxFrac) * 2.2, -1, 1);
        pointer.y = clamp(((e.clientY - b.top) / b.height - cyFrac) * 2.2, -1, 1);
      };
      window.addEventListener("pointermove", onMove, { passive: true });

      // ---- blink & saccade state
      let nextBlink = 1.2, blinkStart = -10, doubleBlink = false;
      let sacc = { x: 0, y: 0 }, nextSacc = 0.8;
      const blinkAmount = (t: number) => {   // 0 open → 1 closed
        const dt = t - blinkStart;
        const one = (u: number) => (u < 0 ? 0 : u < 0.09 ? ease(u / 0.09) : u < 0.13 ? 1 : u < 0.31 ? 1 - ease((u - 0.13) / 0.18) : 0);
        return Math.max(one(dt), doubleBlink ? one(dt - 0.36) : 0);
      };

      const v = new THREE.Vector3();
      const toScreen = (x: number, y: number, z: number) => {
        v.set(x, y, z).project(camera);
        return [(v.x * 0.5 + 0.5) * W, (-v.y * 0.5 + 0.5) * H];
      };

      let shown = 0, raf = 0, visible = true;
      const clock = new THREE.Clock();
      const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && !raf) raf = requestAnimationFrame(tick); });
      io.observe(el);

      function tick() {
        raf = 0;
        if (disposed || !visible) return;
        const t = clock.getElapsedTime();
        const target = progress ? clamp(progress.current) : 0;
        shown += (target - shown) * (reduce ? 1 : 0.1);
        const p = shown;

        const zoom = ease(seg(p, 0.3, 0.66));
        const fade = ease(seg(p, 0.55, 0.78));
        camera.position.set(0, 0, THREE.MathUtils.lerp(dRest, dEnd, zoom));
        camera.lookAt(0, 0, 0);
        camera.updateMatrixWorld();

        // gaze: pointer + idle micro-saccades, recentred while zooming
        if (!reduce && t > nextSacc) { sacc = { x: (Math.random() - 0.5) * 0.18, y: (Math.random() - 0.5) * 0.12 }; nextSacc = t + 0.8 + Math.random() * 2.2; }
        const look = 1 - zoom;
        const gx = (pointer.x * 0.32 + sacc.x) * look, gy = (pointer.y * 0.22 + sacc.y) * look;
        ball.rotation.y += (gx - ball.rotation.y) * (reduce ? 1 : 0.22);
        ball.rotation.x += (gy - ball.rotation.x) * (reduce ? 1 : 0.22);

        // blinking (only while the eye is shown whole)
        if (!reduce && t > nextBlink && zoom < 0.05) {
          blinkStart = t; doubleBlink = Math.random() < 0.18; nextBlink = t + 2.6 + Math.random() * 3.6;
        }
        const closed = reduce ? 0 : blinkAmount(t) * (1 - zoom);

        // pupil: gentle hippus, constricts slightly after a blink, dilates while zooming in
        const hippus = reduce ? 0 : Math.sin(t * 0.9) * 0.012 + Math.sin(t * 2.3) * 0.006;
        irisUniforms.uPupil.value = THREE.MathUtils.lerp(0.34 + hippus - closed * 0.02, 0.93, zoom);
        irisUniforms.uFundusMix.value = ease(seg(p, 0.36, 0.6));
        irisUniforms.uIrisAlpha.value = 1 - fade;
        sMat.opacity = 1 - ease(seg(p, 0.3, 0.46));      // eyeball fades before it grows over the text
        gMat.opacity = 0.9 * (1 - ease(seg(p, 0.4, 0.62)));
        irisUniforms.uTime.value = reduce ? 0.3 : t;
        irisUniforms.uScan.value = ease(seg(p, 0.74, 0.86));
        irisUniforms.uHeat.value = ease(seg(p, 0.86, 1));

        // eyelid aperture (CSS clip-path on the canvas) + lashes overlay
        const open = 1 - closed;
        const expand = ease(seg(p, 0.27, 0.35));
        const [cx, cy] = toScreen(0, 0, 0);
        const [ex] = toScreen(1, 0, 0);
        const u = Math.abs(ex - cx);                    // pixels per world unit at the iris plane
        const s = u * (1 + expand * 12);
        const halfW = 2.45 * s, up = 0.92 * s, lo = 0.98 * s;
        const upY = THREE.MathUtils.lerp(-0.12 * s, up, open), loY = THREE.MathUtils.lerp(0.14 * s, lo, Math.max(open, 0.25));
        const L = [cx - halfW, cy + 0.06 * s], Rr = [cx + halfW, cy - 0.02 * s];
        const upper = `M ${L[0]} ${L[1]} C ${cx - halfW * 0.55} ${cy - upY * 1.32} ${cx + halfW * 0.4} ${cy - upY * 1.36} ${Rr[0]} ${Rr[1]}`;
        const lower = `C ${cx + halfW * 0.5} ${cy + loY * 1.22} ${cx - halfW * 0.45} ${cy + loY * 1.28} ${L[0]} ${L[1]} Z`;
        const d = `${upper} ${lower}`;
        canvas.style.clipPath = expand >= 0.999 ? "none" : `path('${d}')`;

        const lidAlpha = 1 - ease(seg(p, 0.27, 0.34));   // skin and lashes leave before the zoom grows
        ov.style.opacity = String(lidAlpha);
        skin.style.opacity = String(lidAlpha);
        const cub = (pts: number[][], tt: number) => {
          const a = 1 - tt;
          return [0, 1].map((i) => a ** 3 * pts[0][i] + 3 * a * a * tt * pts[1][i] + 3 * a * tt * tt * pts[2][i] + tt ** 3 * pts[3][i]);
        };
        const UP = [L, [cx - halfW * 0.55, cy - upY * 1.32], [cx + halfW * 0.4, cy - upY * 1.36], Rr];
        const LO = [Rr, [cx + halfW * 0.5, cy + loY * 1.22], [cx - halfW * 0.45, cy + loY * 1.28], L];
        if (lidAlpha > 0.01) {
          // ---- skin (behind the eye; visible around it and over the eye when the lids close)
          sk.clearRect(0, 0, W, H);
          sk.save();
          const rx = halfW * 1.38, ry = halfW * 0.98;
          sk.translate(cx, cy - 0.15 * s); sk.scale(rx, ry);
          const feather = sk.createRadialGradient(0, 0, 0, 0, 0, 1);
          feather.addColorStop(0, "rgba(196,150,122,1)");
          feather.addColorStop(0.5, "rgba(201,156,128,1)");
          feather.addColorStop(0.78, "rgba(216,180,158,0.6)");
          feather.addColorStop(1, "rgba(244,248,252,0)");
          sk.fillStyle = feather; sk.beginPath(); sk.arc(0, 0, 1, 0, Math.PI * 2); sk.fill();
          sk.restore();
          sk.save();
          sk.beginPath(); sk.ellipse(cx, cy - 0.15 * s, rx, ry, 0, 0, Math.PI * 2); sk.clip();
          sk.globalAlpha = 0.9; sk.fillStyle = grainPat; sk.fillRect(cx - rx, cy - ry - 0.15 * s, rx * 2, ry * 2); sk.globalAlpha = 1;
          const curve = (pts: number[][], dy: number, grow: number) => {
            sk.beginPath();
            sk.moveTo(pts[0][0] - grow, pts[0][1] + dy * 0.4);
            sk.bezierCurveTo(pts[1][0], pts[1][1] + dy, pts[2][0], pts[2][1] + dy, pts[3][0] + grow, pts[3][1] + dy * 0.4);
          };
          const soft = (w: number, col: string, blur: number) => { sk.lineWidth = w; sk.strokeStyle = col; sk.filter = `blur(${blur}px)`; sk.stroke(); sk.filter = "none"; };
          const crease = -0.62 * s - (up - upY) * 0.25;
          curve([L, [cx - halfW * 0.55, cy - up * 1.32], [cx + halfW * 0.4, cy - up * 1.36], Rr], crease - 0.35 * s, 0.25 * s);
          soft(0.55 * s, "rgba(232,198,176,0.55)", 0.18 * s);       // brow-bone highlight
          curve([L, [cx - halfW * 0.55, cy - up * 1.32], [cx + halfW * 0.4, cy - up * 1.36], Rr], crease, 0.1 * s);
          soft(0.2 * s, "rgba(92,52,36,0.42)", 0.09 * s);           // lid crease
          curve(UP, -0.2 * s, 0);
          soft(0.26 * s, "rgba(236,204,184,0.4)", 0.08 * s);        // lit upper-lid skin
          curve(LO, 0.2 * s, 0);
          soft(0.22 * s, "rgba(110,64,46,0.28)", 0.12 * s);         // under-eye shading
          curve(LO, 0.08 * s, 0);
          soft(0.05 * s, "rgba(232,180,170,0.75)", 0.01 * s);       // lower-lid waterline
          const corner = sk.createRadialGradient(L[0] - 0.1 * s, L[1], 0, L[0] - 0.1 * s, L[1], 0.7 * s);
          corner.addColorStop(0, "rgba(90,50,40,0.35)"); corner.addColorStop(1, "rgba(90,50,40,0)");
          sk.fillStyle = corner; sk.fillRect(L[0] - 0.8 * s, L[1] - 0.8 * s, 1.6 * s, 1.6 * s);
          // upper-lid margin seen when closing
          curve(UP, 0, 0);
          soft(0.07 * s, "rgba(70,40,30,0.75)", 0.012 * s);
          sk.restore();

          // ---- lashes as tapered filled strands
          let lashes = "";
          const strand = (bx: number, by: number, dx: number, dy: number, len: number, curl: number, w: number) => {
            const tx = bx + dx * len, ty = by + dy * len;
            const px = -dy, py = dx;
            const cxl = bx + dx * len * 0.55 + px * curl * len * 0.3, cyl = by + dy * len * 0.55 + py * curl * len * 0.3 - len * curl * 0.25;
            lashes += `M ${bx + px * w} ${by + py * w} Q ${cxl} ${cyl} ${tx} ${ty} Q ${cxl - px * w * 0.6} ${cyl - py * w * 0.6} ${bx - px * w} ${by - py * w} Z `;
          };
          for (const l of LASH) {
            const [x, y] = cub(UP, l.t), [x2, y2] = cub(UP, Math.min(1, l.t + 0.01));
            let nx = y2 - y, ny = -(x2 - x);
            const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
            if (ny > 0) { nx = -nx; ny = -ny; }
            const fan = (l.t - 0.42) * 1.1 + l.ang;
            let dx = nx * Math.cos(fan) - ny * Math.sin(fan), dy = nx * Math.sin(fan) + ny * Math.cos(fan);
            // as the lid closes the lashes swing down and outwards with it
            const down = ease(clamp(closed * 1.15));
            dx = dx * (1 - down) + (l.t - 0.45) * 0.9 * down; dy = dy * (1 - down) + 0.95 * down;
            const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
            const len = s * (0.12 + 0.17 * Math.sin(Math.PI * Math.min(1, l.t * 1.1))) * l.len * (l.row ? 0.8 : 1);
            strand(x - nx * 0.02 * s * l.row, y - ny * 0.02 * s * l.row, dx, dy, len, l.curl * (dx > 0 ? -1 : 1), 0.011 * s * l.w);
          }
          let low = "";
          for (const l of LOW) {
            const [x, y] = cub(LO, l.t), [x2, y2] = cub(LO, Math.min(1, l.t + 0.01));
            let nx = y2 - y, ny = -(x2 - x);
            const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
            if (ny < 0) { nx = -nx; ny = -ny; }
            const len = s * 0.07 * l.len, a = l.ang - (0.5 - l.t) * 0.6;
            const dx = nx * Math.cos(a) - ny * Math.sin(a), dy = nx * Math.sin(a) + ny * Math.cos(a);
            const w = 0.006 * s;
            low += `M ${x - dy * w} ${y + dx * w} L ${x + dx * len} ${y + dy * len} L ${x + dy * w} ${y - dx * w} Z `;
          }
          (ov.querySelector("#lash") as SVGPathElement).setAttribute("d", lashes);
          (ov.querySelector("#lashlow") as SVGPathElement).setAttribute("d", low);
          (ov.querySelector("#lidshadow") as SVGPathElement).setAttribute("d", upper);
          (ov.querySelector("#aperture") as SVGPathElement).setAttribute("d", d);
          for (const [id, x] of [["#cornerL", L[0] + 0.35 * s], ["#cornerR", Rr[0] - 0.35 * s]] as const) {
            const e = ov.querySelector(id) as SVGEllipseElement;
            e.setAttribute("cx", String(x)); e.setAttribute("cy", String(cy)); e.setAttribute("rx", String(0.9 * s)); e.setAttribute("ry", String(0.9 * s));
          }
          const car = ov.querySelector("#caruncle") as SVGEllipseElement;
          car.setAttribute("cx", String(L[0] + 0.24 * s)); car.setAttribute("cy", String(L[1] + 0.01 * s));
          car.setAttribute("rx", String(0.17 * s)); car.setAttribute("ry", String(Math.max(0.5, 0.11 * s * open)));
          ov.querySelectorAll<SVGElement>(".sw").forEach((n) => n.setAttribute("stroke-width", String(Number(n.dataset.w) * u)));
        }

        renderer.render(scene, camera);
        raf = requestAnimationFrame(tick);
      }
      raf = requestAnimationFrame(tick);

      cleanup = () => {
        cancelAnimationFrame(raf);
        ro.disconnect(); io.disconnect();
        window.removeEventListener("pointermove", onMove);
        [irisTex, fundusTex, scleraTex, glintTex].forEach((x) => x.dispose());
        sGeo.dispose(); iGeo.dispose(); sMat.dispose(); iMat.dispose(); gMat.dispose();
        renderer.dispose(); canvas.remove();
      };
    });
    return () => { disposed = true; cleanup(); };
  }, [progress, layout]);

  return (
    <div ref={host} aria-hidden className={className} style={{ position: "absolute", inset: 0 }}>
      <svg ref={svg} className="pointer-events-none absolute inset-0 h-full w-full" style={{ opacity: 0 }}>
        <defs>
          <clipPath id="eye-ap"><path id="aperture" /></clipPath>
          <filter id="eye-soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6" /></filter>
          <radialGradient id="corner-g"><stop offset="0" stopColor="#5a3a30" stopOpacity="0.38" /><stop offset="1" stopColor="#5a3a30" stopOpacity="0" /></radialGradient>
          <radialGradient id="car-g" cx="0.45" cy="0.4"><stop offset="0" stopColor="#f0b3ac" /><stop offset="0.6" stopColor="#d98f8a" /><stop offset="1" stopColor="#c97f7c" stopOpacity="0" /></radialGradient>
        </defs>
        <g clipPath="url(#eye-ap)">
          <path id="lidshadow" className="sw" data-w="0.34" fill="none" stroke="#3a2016" strokeOpacity="0.42" filter="url(#eye-soft)" />
          <ellipse id="cornerL" fill="url(#corner-g)" />
          <ellipse id="cornerR" fill="url(#corner-g)" />
          <ellipse id="caruncle" fill="url(#car-g)" />
        </g>
        <path id="lashlow" fill="#2b1d17" fillOpacity="0.55" />
        <path id="lash" fill="#1f1511" fillOpacity="0.92" />
      </svg>
    </div>
  );
}
