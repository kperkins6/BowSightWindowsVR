'use strict';
// Dependency-free WebGL geometry viewer. Both panels share one camera.
class BowViewer {
  constructor(before, after) {
    this.canvases=[before,after];this.views=[];this.yaw=.25;this.pitch=.12;this.zoom=1;this.pan=[0,0];this.wire=false;this.guides=true;
    for (const canvas of this.canvases) {
      const gl=canvas.getContext('webgl',{antialias:true,alpha:false});
      if(!gl)throw new Error('WebGL is unavailable. Enable browser hardware acceleration to preview bows.');
      const shader=(type,src)=>{let s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
      const program=gl.createProgram();
      gl.attachShader(program,shader(gl.VERTEX_SHADER,`attribute vec3 p;attribute vec3 n;uniform mat4 m;varying vec3 normal;void main(){gl_Position=m*vec4(p,1.);normal=n;}`));
      gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`precision mediump float;varying vec3 normal;uniform vec3 color;uniform float unlit;void main(){vec3 n=normalize(normal);float light=.28+.55*abs(dot(n,normalize(vec3(.5,.7,1.))))+.17*abs(n.y);gl_FragColor=vec4(color*mix(light,1.,unlit),1.);}`));
      gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
      this.views.push({gl,program,p:gl.getAttribLocation(program,'p'),n:gl.getAttribLocation(program,'n'),m:gl.getUniformLocation(program,'m'),color:gl.getUniformLocation(program,'color'),flat:gl.getUniformLocation(program,'unlit'),buffers:[]});
      let drag=null;
      canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
      canvas.addEventListener('pointerup',()=>drag=null);
      canvas.addEventListener('pointercancel',()=>drag=null);
      canvas.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];drag=[e.clientX,e.clientY];if(e.shiftKey){this.pan[0]+=dx/canvas.clientWidth*this.span/this.zoom;this.pan[1]-=dy/canvas.clientHeight*this.span/this.zoom;}else{this.yaw+=dx*.009;this.pitch=Math.max(-1.4,Math.min(1.4,this.pitch+dy*.009));}this.render();});
      canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.25,Math.min(30,this.zoom*Math.exp(-e.deltaY*.001)));this.render();},{passive:false});
    }
    this.resize=new ResizeObserver(()=>this.render());this.canvases.forEach(c=>this.resize.observe(c));
  }
  upload(view, positions, triangles, color, line=false) {
    const {gl}=view, vertices=[],normals=[];
    for(const t of triangles){let [a,b,c]=t.map(i=>positions[i]);if(!a||!b||!c)continue;let u=b.map((v,i)=>v-a[i]),v=c.map((q,i)=>q-a[i]);let n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];let len=Math.hypot(...n)||1;n=n.map(x=>x/len);
      for(const i of (line?[0,1,1,2,2,0]:[0,1,2])){vertices.push(...[a,b,c][i]);normals.push(...n);}}
    const pb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,pb);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    const nb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,nb);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(normals),gl.STATIC_DRAW);
    return {pb,nb,count:vertices.length/3,color,line};
  }
  set(data,settings,reset=true) {
    this.data=data;this.settings=settings;
    let min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(const shape of data.shapes)for(const q of shape.before)for(let i=0;i<3;i++){min[i]=Math.min(min[i],q[i]);max[i]=Math.max(max[i],q[i]);}
    this.fullCenter=min.map((v,i)=>(v+max[i])/2);this.fullSpan=Math.max(...max.map((v,i)=>v-min[i]))*1.12;
    for(let i=0;i<2;i++){const view=this.views[i],{gl}=view;for(const b of view.buffers){gl.deleteBuffer(b.pb);gl.deleteBuffer(b.nb);}view.buffers=[];
      for(const shape of data.shapes){const positions=shape[i?'after':'before'],triangles=shape[i?'triangles':'beforeTriangles'];const color=i&&shape.editable&&shape.enabled?[.79,.76,.66]:[.64,.7,.73];view.buffers.push(this.upload(view,positions,triangles,color));view.buffers.push(this.upload(view,positions,triangles,[.23,.31,.35],true));}}
    if(reset||!this.center)this.fit();else if(this.focused)this.focus();else this.render();
  }
  fit(){if(!this.data)return;this.focused=false;this.center=this.fullCenter.slice();this.span=this.fullSpan;this.zoom=1;this.pan=[0,0];this.render();}
  focus(){if(!this.data)return;this.focused=true;this.center=[0,this.settings.shelf+this.settings.height/2,0];this.span=this.settings.height*1.6;this.zoom=1;this.pan=[0,0];this.render();}
  angle(yaw,pitch=0){this.yaw=yaw;this.pitch=pitch;this.render();}
  matrix(aspect){const cy=Math.cos(this.yaw),sy=Math.sin(this.yaw),cp=Math.cos(this.pitch),sp=Math.sin(this.pitch),s=2*this.zoom/this.span;
    // Camera front looks along model X: model Z is screen horizontal, Y vertical.
    const rx=[sy,0,cy],ry=[-sp*cy,cp,sp*sy],rz=[-cp*cy,-sp,cp*sy];const c=this.center;
    const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0);const xs=s/aspect,ys=s,zs=1/(this.fullSpan*3);
    return new Float32Array([rx[0]*xs,ry[0]*ys,rz[0]*zs,0,rx[1]*xs,ry[1]*ys,rz[1]*zs,0,rx[2]*xs,ry[2]*ys,rz[2]*zs,0,(-dot(rx,c)+this.pan[0])*xs,(-dot(ry,c)+this.pan[1])*ys,-dot(rz,c)*zs,1]);}
  render(){if(!this.data||!this.center)return;for(const view of this.views){const {gl,program}=view,c=gl.canvas,dpr=Math.min(devicePixelRatio||1,2),w=Math.round(c.clientWidth*dpr),h=Math.round(c.clientHeight*dpr);if(!w||!h)continue;if(c.width!==w||c.height!==h){c.width=w;c.height=h;}gl.viewport(0,0,w,h);gl.clearColor(.062,.09,.113,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.useProgram(program);gl.uniformMatrix4fv(view.m,false,this.matrix(w/h));
      const draw=b=>{gl.bindBuffer(gl.ARRAY_BUFFER,b.pb);gl.enableVertexAttribArray(view.p);gl.vertexAttribPointer(view.p,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ARRAY_BUFFER,b.nb);gl.enableVertexAttribArray(view.n);gl.vertexAttribPointer(view.n,3,gl.FLOAT,false,0,0);gl.uniform3fv(view.color,b.color);gl.uniform1f(view.flat,b.line?1:0);gl.drawArrays(b.line?gl.LINES:gl.TRIANGLES,0,b.count);};
      gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);for(const b of view.buffers)if(!b.line)draw(b);gl.disable(gl.POLYGON_OFFSET_FILL);if(this.wire)for(const b of view.buffers)if(b.line)draw(b);
      if(this.guides){const s=this.settings.shelf,t=s+this.settings.height;const p=[[-7,s,-7],[-7,s,7],[7,s,7],[7,s,-7],[-7,t,-7],[-7,t,7],[7,t,7],[7,t,-7]];const b=this.upload(view,p,[[0,1,2],[0,2,3],[4,5,6],[4,6,7]],[.61,.43,.25],true);gl.disable(gl.DEPTH_TEST);draw(b);gl.deleteBuffer(b.pb);gl.deleteBuffer(b.nb);}}
  }
}
window.BowViewer=BowViewer;
