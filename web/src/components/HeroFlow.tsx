import { useEffect, useRef } from "react";
import { useTheme } from "../theme";

const vertex = `attribute vec2 aPosition; varying vec2 vUv;
void main(){vUv=aPosition*.5+.5;gl_Position=vec4(aPosition,0.,1.);}`;
// Original single-pass shader: artwork-preserving displacement, not a fluid solver.
const fragment = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 vUv;
uniform sampler2D uImage;
uniform vec2 uResolution, uImageSize;
uniform float uTime;
uniform vec4 uTrail[12];
void main(){
  vec2 uv=vUv;
  float aspect=uResolution.x/uResolution.y;
  float artMask=smoothstep(.28,.68,uv.x);
  vec2 drift=vec2(sin(uv.y*7.+uTime*.25)+sin(uv.x*5.-uTime*.17),cos(uv.x*6.+uTime*.21));
  vec2 offset=drift*.006*artMask;
  float glint=0.;
  for(int i=0;i<12;i++){
    vec4 p=uTrail[i];
    vec2 d=(uv-p.xy)*vec2(aspect,1.);
    float radius=length(d);
    float age=uTime-p.z;
    float alive=step(0.,age)*exp(-max(age,0.)*1.9)*p.w;
    float brush=exp(-dot(d,d)*48.);
    float wave=sin(radius*35.-age*4.5);
    offset+=(d/vec2(aspect,1.))*(brush*wave*alive*.12);
    glint+=brush*alive*.008;
  }
  // Cover crop remains identical to the CSS fallback at every aspect ratio.
  float imageAspect=uImageSize.x/uImageSize.y;
  vec2 crop=vec2(min(aspect/imageAspect,1.),min(imageAspect/aspect,1.));
  vec2 sampleUv=(uv-.5+offset)*crop/1.035+.5;
  vec3 base=texture2D(uImage,clamp(sampleUv,.001,.999)).rgb;
  // Restrained optical separation only in moving glass, never over text.
  float split=length(offset)*.045*artMask;
  base.r=mix(base.r,texture2D(uImage,sampleUv+vec2(split,0.)).r,.45);
  base.b=mix(base.b,texture2D(uImage,sampleUv-vec2(split,0.)).b,.45);
  gl_FragColor=vec4(base+glint*artMask,1.);
}`;

export function HeroFlow() {
  const { theme } = useTheme();
  const ref = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const layer = ref.current;
    const canvas = canvasRef.current;
    const shell = layer?.closest<HTMLElement>(".hero-shell");
    if (!layer || !canvas || !shell) return;
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    if (motion.matches) return;
    const gl = canvas.getContext("webgl", { alpha: false, antialias: false, powerPreference: "low-power" });
    if (!gl) return;
    let disposed = false, frame = 0, visible = true, loaded = false;
    let previous = { x: -1, y: -1, time: 0 }, lastStamp = 0, cursor = 0;
    const started = performance.now();
    const trails = new Float32Array(48);
    const shaders: WebGLShader[] = [];
    const program = gl.createProgram();
    const buffer = gl.createBuffer();
    const texture = gl.createTexture();
    const image = new Image();
    if (!program || !buffer || !texture) return;
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) throw new Error("Shader allocation failed");
      shaders.push(shader);
      gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error("Shader compilation failed");
      gl.attachShader(program, shader);
    };
    const cleanupGpu = () => {
      shaders.forEach(shader => gl.deleteShader(shader));
      gl.deleteProgram(program); gl.deleteBuffer(buffer); gl.deleteTexture(texture);
    };
    try {
      compile(gl.VERTEX_SHADER, vertex); compile(gl.FRAGMENT_SHADER, fragment);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error("Shader link failed");
    } catch { cleanupGpu(); return; }
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, "aPosition");
    gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const resolution = gl.getUniformLocation(program, "uResolution");
    const time = gl.getUniformLocation(program, "uTime");
    const trail = gl.getUniformLocation(program, "uTrail[0]");
    gl.uniform1i(gl.getUniformLocation(program, "uImage"), 0);
    const resize = () => {
      const rect = shell.getBoundingClientRect();
      // Match HiDPI displays without exceeding GPU texture/viewport limits.
      const maxTexture = gl.getParameter(gl.MAX_TEXTURE_SIZE) as number;
      const maxViewport = gl.getParameter(gl.MAX_VIEWPORT_DIMS) as Int32Array;
      const dpr = Math.min(devicePixelRatio || 1, 2, maxTexture / Math.max(rect.width, rect.height, 1), maxViewport[0] / Math.max(rect.width, 1), maxViewport[1] / Math.max(rect.height, 1));
      canvas.width = Math.max(1, Math.round(rect.width*dpr));
      canvas.height = Math.max(1, Math.round(rect.height*dpr));
      gl.viewport(0,0,canvas.width,canvas.height);
      gl.uniform2f(resolution, canvas.width, canvas.height);
    };
    const stop = () => { cancelAnimationFrame(frame); frame = 0; };
    const draw = (now: number) => {
      frame = 0;
      if (disposed || !visible || document.hidden || motion.matches || !loaded) return;
      gl.uniform1f(time, (now-started)/1000);
      gl.uniform4fv(trail, trails);
      gl.drawArrays(gl.TRIANGLES,0,6);
      layer.classList.add("webgl-ready");
      frame = requestAnimationFrame(draw);
    };
    const resume = () => {
      stop();
      if (motion.matches) layer.classList.remove("webgl-ready");
      else if (loaded && visible && !document.hidden) frame = requestAnimationFrame(draw);
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType === "touch" || motion.matches) return;
      const now = performance.now(), rect = shell.getBoundingClientRect();
      const x = (event.clientX-rect.left)/rect.width, y = 1-(event.clientY-rect.top)/rect.height;
      if (previous.x >= 0 && now-lastStamp > 35) {
        const speed = Math.hypot(x-previous.x,y-previous.y)/Math.max((now-previous.time)/1000,.016);
        trails.set([x,y,(now-started)/1000,Math.min(speed*1.8,.85)],cursor*4);
        cursor=(cursor+1)%12; lastStamp=now;
      }
      previous={x,y,time:now};
    };
    const leave = () => { previous.x=-1; };
    const lost = (event: Event) => { event.preventDefault(); stop(); loaded=false; layer.classList.remove("webgl-ready"); };
    const observer = new ResizeObserver(resize); observer.observe(shell);
    const intersection = new IntersectionObserver(entries => { visible=entries[0].isIntersecting; resume(); }); intersection.observe(shell);
    shell.addEventListener("pointermove",move); shell.addEventListener("pointerleave",leave);
    document.addEventListener("visibilitychange",resume); motion.addEventListener("change",resume);
    canvas.addEventListener("webglcontextlost",lost);
    image.onload=()=>{
      if (disposed) return;
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,image);
      gl.uniform2f(gl.getUniformLocation(program,"uImageSize"),image.naturalWidth,image.naturalHeight);
      resize(); loaded=true; resume();
    };
    image.src=`/media/hero-glass-${theme}-original.png`;
    return ()=>{
      disposed=true; stop(); image.onload=null;
      observer.disconnect(); intersection.disconnect();
      shell.removeEventListener("pointermove",move); shell.removeEventListener("pointerleave",leave);
      document.removeEventListener("visibilitychange",resume); motion.removeEventListener("change",resume);
      canvas.removeEventListener("webglcontextlost",lost);
      layer.classList.remove("webgl-ready"); cleanupGpu();
    };
  }, [theme]);
  return <div ref={ref} className="hero-art" aria-hidden="true">
    <div className="hero-art-image" />
    <canvas ref={canvasRef} className="hero-liquid-canvas" />
  </div>;
}
