<script setup lang="ts">
/** M01 UI page 1 — Sign-in email step, route /login (FDD §2.1.2). */
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import logoIcon from '@/assets/logo_icon.svg'
import bgUrlA from '@/assets/bg.png'
import bgUrlB from '@/assets/bg2.png'
import { useLoginFlow } from '@/views/auth/hooks/useLoginFlow'

const router = useRouter()
const flow = useLoginFlow()

async function submit() {
  if (await flow.requestCode()) router.push('/login/verify')
}

/* Hero background cycle: bg.png and bg2.png alternate with a 5s hold and a 2s
   glitch/datamosh transition. The held images are the plain CSS layers below;
   the glitch is rendered on a WebGL canvas shown ONLY during the 2s morph, so
   distortion never touches a resting frame (a held image is pixel-identical to
   the source). No WebGL → calm CSS cross-fade; reduced motion → static image. */
const HOLD_MS = 5000
const TRANS_MS = 2000

const glitchCanvas = ref<HTMLCanvasElement | null>(null)
const showB = ref(false) // which source image is the resting layer (false → bg.png)
const glitchActive = ref(false) // canvas overlay is opaque only mid-transition

let stop = () => {}

onMounted(() => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return // static bg.png
  const canvas = glitchCanvas.value
  const gl = canvas
    ? (canvas.getContext('webgl', { alpha: false, antialias: true }) as WebGLRenderingContext | null)
    : null
  try {
    stop = gl ? startGlitch(canvas!, gl) : startCrossfade()
  } catch {
    stop = startCrossfade()
  }
})

onBeforeUnmount(() => stop())

/** Fallback when WebGL is unavailable: bg2.png cross-fades over bg.png (CSS). */
function startCrossfade() {
  let timer = window.setTimeout(function tick() {
    showB.value = !showB.value
    timer = window.setTimeout(tick, HOLD_MS + TRANS_MS)
  }, HOLD_MS)
  return () => window.clearTimeout(timer)
}

function startGlitch(canvas: HTMLCanvasElement, gl: WebGLRenderingContext) {
  const VERT = `attribute vec2 aPos; varying vec2 vUv;
    void main(){ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }`
  const FRAG = `precision highp float;
    varying vec2 vUv;
    uniform sampler2D uFrom, uTo;
    uniform float uP, uTime;
    uniform vec2 uRes, uImg;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123); }
    vec2 cover(vec2 uv){
      float ca = uRes.x / uRes.y, ia = uImg.x / uImg.y;
      if (ca > ia) { uv.y = (uv.y - 0.5) * (ia / ca) + 0.5; }
      else { uv.x = (uv.x - 0.5) * (ca / ia) + 0.5; }
      return uv;
    }
    void main(){
      vec2 base = cover(vUv);
      float P = uP;
      float tf = 4.0 * P * (1.0 - P); // 0 at the ends, 1 mid-transition
      float by = floor(vUv.y * 22.0);
      float ta = floor(uTime * 11.0);
      float jt = hash(vec2(by, ta));
      float sh = step(0.65, jt) * (jt - 0.5) * 0.5 * tf;
      vec2 g = base + vec2(sh, 0.0);
      float blk = hash(vec2(by, floor(uTime * 9.0) + 2.0)) * 0.7 + 0.15;
      float thr = smoothstep(blk - 0.12, blk + 0.12, P);
      float rs = 0.02 * tf * step(0.5, hash(vec2(by, ta + 5.0)));
      float R = mix(texture2D(uFrom, g + vec2(rs, 0.0)).r, texture2D(uTo, g + vec2(rs, 0.0)).r, thr);
      float G = mix(texture2D(uFrom, g).g, texture2D(uTo, g).g, thr);
      float B = mix(texture2D(uFrom, g - vec2(rs, 0.0)).b, texture2D(uTo, g - vec2(rs, 0.0)).b, thr);
      vec3 col = vec3(R, G, B);
      col *= mix(1.0, 0.88 + 0.12 * sin(vUv.y * uRes.y * 1.6), tf); // scanlines
      col += vec3(0.1, 0.5, 0.6) * tf * step(0.82, hash(vec2(by, ta))) * 0.3; // cyan blocks
      gl_FragColor = vec4(col, 1.0);
    }`

  const compile = (type: number, src: string) => {
    const s = gl.createShader(type)!
    gl.shaderSource(s, src)
    gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader')
    return s
  }
  const prog = gl.createProgram()!
  gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT))
  gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG))
  gl.linkProgram(prog)
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) || 'link')
  gl.useProgram(prog)

  const quad = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, quad)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
  const aPos = gl.getAttribLocation(prog, 'aPos')
  gl.enableVertexAttribArray(aPos)
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0)

  const uFrom = gl.getUniformLocation(prog, 'uFrom')
  const uTo = gl.getUniformLocation(prog, 'uTo')
  const uP = gl.getUniformLocation(prog, 'uP')
  const uTime = gl.getUniformLocation(prog, 'uTime')
  const uRes = gl.getUniformLocation(prog, 'uRes')
  const uImg = gl.getUniformLocation(prog, 'uImg')
  gl.uniform1i(uFrom, 0)
  gl.uniform1i(uTo, 1)

  let imgW = 1
  let imgH = 1
  const makeTex = (img: HTMLImageElement) => {
    const t = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, t)
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    return t
  }

  let destroyed = false
  let raf = 0
  let timer = 0
  let texA: WebGLTexture | null = null
  let texB: WebGLTexture | null = null

  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const w = Math.max(2, Math.round(canvas.clientWidth * dpr))
    const h = Math.max(2, Math.round(canvas.clientHeight * dpr))
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w
      canvas.height = h
    }
    gl.viewport(0, 0, canvas.width, canvas.height)
  }

  const transition = (fromIsB: boolean) => {
    if (destroyed) return
    resize()
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_2D, fromIsB ? texB : texA)
    gl.activeTexture(gl.TEXTURE1)
    gl.bindTexture(gl.TEXTURE_2D, fromIsB ? texA : texB)
    glitchActive.value = true // reveal the opaque canvas (first frame = pure source)
    showB.value = !fromIsB // settle the destination CSS layer behind the canvas
    const start = performance.now()
    const frame = (now: number) => {
      if (destroyed) return
      const p = Math.min((now - start) / TRANS_MS, 1)
      gl.uniform1f(uP, p)
      gl.uniform1f(uTime, now * 0.001)
      gl.uniform2f(uRes, canvas.width, canvas.height)
      gl.uniform2f(uImg, imgW, imgH)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
      if (p < 1) {
        raf = requestAnimationFrame(frame)
      } else {
        glitchActive.value = false // hide canvas → pixel-identical CSS layer shows
        timer = window.setTimeout(() => transition(!fromIsB), HOLD_MS)
      }
    }
    raf = requestAnimationFrame(frame)
  }

  let loaded = 0
  const onReady = () => {
    if (++loaded < 2 || destroyed) return
    timer = window.setTimeout(() => transition(false), HOLD_MS)
  }
  const load = (url: string, set: (t: WebGLTexture | null) => void) => {
    const img = new Image()
    img.onload = () => {
      imgW = img.naturalWidth
      imgH = img.naturalHeight
      set(makeTex(img))
      onReady()
    }
    img.src = url
  }
  load(bgUrlA, (t) => (texA = t))
  load(bgUrlB, (t) => (texB = t))

  return () => {
    destroyed = true
    cancelAnimationFrame(raf)
    window.clearTimeout(timer)
    gl.getExtension('WEBGL_lose_context')?.loseContext()
  }
}
</script>

<template>
  <div class="login-hero">
    <div class="login-hero-bg login-hero-bg--a" aria-hidden="true"></div>
    <div class="login-hero-bg login-hero-bg--b" :style="{ opacity: showB ? 1 : 0 }" aria-hidden="true"></div>
    <canvas
      ref="glitchCanvas"
      class="login-hero-glitch"
      :class="{ 'is-active': glitchActive }"
      aria-hidden="true"
    ></canvas>
    <div class="login-card">
      <div class="login-brand">
        <img class="login-logo" :src="logoIcon" alt="ZqOmni logo" />
        <h1 class="login-title">ZqOmni</h1>
      </div>
      <p class="login-subtitle">
        Physical AI Data &amp; Compute Infrastructure Platform
      </p>
      <form class="login-form" @submit.prevent="submit">
        <div class="field">
          <input
            id="email"
            aria-label="Email"
            v-model="flow.email.value"
            class="text-input"
            type="email"
            placeholder="name@company.com"
            autocomplete="email"
            maxlength="254"
            required
            @blur="flow.email.value && flow.validateEmail()"
          />
          <span v-if="flow.emailError.value" class="field-error">{{ flow.emailError.value }}</span>
        </div>
        <button
          class="btn btn-primary login-submit"
          type="submit"
          :disabled="flow.submitting.value || flow.retryAfter.value > 0"
        >
          <span v-if="flow.retryAfter.value > 0">Too many requests. Try again in {{ flow.retryAfter.value }}s</span>
          <span v-else-if="flow.submitting.value">Sending…</span>
          <span v-else>Send code</span>
        </button>
      </form>
      <p class="login-footnote">
        Access requires a pre-registered corporate email. A one-time code will be sent if the
        email is registered.
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Robot-fleet hero. bg.png stays a fully-opaque base layer; bg2.png sits above
   it and is toggled on/off (its opacity is driven from script). The 2s glitch
   morph between them is drawn on the WebGL overlay (.login-hero-glitch), which
   is opaque only during the transition — so a held frame is always the plain,
   pixel-identical CSS image. Without WebGL the .login-hero-bg opacity transition
   below provides a calm bg2-over-bg cross-fade; reduced motion stays on bg.png.
   Cycle (14s): bg.png held 5s → 2s glitch → bg2.png held 5s → 2s glitch back. */
.login-hero {
  position: relative;
  overflow: hidden;
  min-height: 100vh;
  background-color: color-mix(in srgb, var(--color-brand-navy) 60%, #7985a2);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}
.login-hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: opacity 2s ease-in-out;
}
.login-hero-bg--a {
  background-image: url('../../assets/bg.png');
}
.login-hero-bg--b {
  background-image: url('../../assets/bg2.png');
  opacity: 0;
}
.login-hero-glitch {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  opacity: 0;
  pointer-events: none;
}
.login-hero-glitch.is-active {
  opacity: 1;
}
@media (prefers-reduced-motion: reduce) {
  .login-hero-bg { transition: none; }
}
.login-card {
  position: relative;
  z-index: 2;
  width: min(420px, 100%);
  background: var(--color-canvas);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: var(--rounded-lg);
  /* Edge depth against the bright hero: light-catching rim on the top edge,
     tight contact shadow, then deep navy-toned ambient falloff. */
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 1px 2px rgba(10, 21, 48, 0.16),
    0 12px 28px -8px rgba(10, 21, 48, 0.28),
    0 32px 64px -16px rgba(10, 21, 48, 0.34);
  padding: var(--space-xxl);
  display: flex;
  flex-direction: column;
}
@supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .login-card {
    background: rgba(255, 255, 255, 0.8);
    -webkit-backdrop-filter: blur(18px) saturate(150%);
    backdrop-filter: blur(18px) saturate(150%);
  }
}
.login-brand {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}
.login-logo {
  width: 40px;
  height: 40px;
  flex: none;
  display: block;
}
.login-title {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.5px;
  color: var(--color-ink);
}
.login-subtitle {
  font-size: 14px;
  color: var(--color-steel);
  margin: var(--space-xs) 0 var(--space-xl);
}
.login-form {
  display: flex;
  flex-direction: column;
}
.login-submit {
  width: 100%;
  justify-content: center;
}
.login-footnote {
  font-size: 13px;
  color: var(--color-steel);
  margin-top: var(--space-lg);
  line-height: 1.4;
}
</style>
