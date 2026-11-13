"""Small local WebGL surface viewer; no network library or geometry edits."""

JS = r'''
(function(){'use strict';if(window.RadaiContourScene)return;
function create(canvas){
 var gl=canvas.getContext('webgl',{alpha:false,antialias:true,preserveDrawingBuffer:false});if(!gl)throw Error('WEBGL_UNAVAILABLE');
 function shader(type,source){var s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error('WEBGL_UNAVAILABLE');return s;}
 var vs=shader(gl.VERTEX_SHADER,'attribute vec3 p;attribute vec3 n;attribute vec3 c;uniform vec3 target;uniform vec2 angle;uniform vec3 scale;varying vec3 color;varying float light;void main(){float ca=cos(angle.x),sa=sin(angle.x),cb=cos(angle.y),sb=sin(angle.y);mat3 rz=mat3(ca,sa,0.,-sa,ca,0.,0.,0.,1.);mat3 rx=mat3(1.,0.,0.,0.,cb,sb,0.,-sb,cb);mat3 r=rx*rz;vec3 q=r*(p-target);gl_Position=vec4(q*scale,1.);vec3 nn=normalize(r*n);light=.3+.7*abs(dot(nn,normalize(vec3(.2,-.3,1.))));color=c;}');
 var fs=shader(gl.FRAGMENT_SHADER,'precision mediump float;varying vec3 color;varying float light;void main(){gl_FragColor=vec4(color*light,1.);}');
 var program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('WEBGL_UNAVAILABLE');
 var buffers=new Map(),uploads=0,count=0,target=[0,0,0],extent=100,yaw=.4,pitch=-1.05,zoom=1,drag=null,disposed=false,scene=null;
 var attrs=['p','n','c'].map(function(k){return gl.getAttribLocation(program,k);}),u={target:gl.getUniformLocation(program,'target'),angle:gl.getUniformLocation(program,'angle'),scale:gl.getUniformLocation(program,'scale')};
 function draw(){if(disposed)return;var rect=canvas.getBoundingClientRect(),ratio=Math.min(2,window.devicePixelRatio||1);if(!rect.width||!rect.height)return;
  var w=Math.max(1,Math.round(rect.width*ratio)),h=Math.max(1,Math.round(rect.height*ratio));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
  gl.viewport(0,0,w,h);gl.clearColor(.015,.025,.045,1);gl.enable(gl.DEPTH_TEST);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);if(!count)return;
  gl.useProgram(program);var aspect=w/h,k=1.7*zoom/extent;gl.uniform3fv(u.target,target);gl.uniform2f(u.angle,yaw,pitch);gl.uniform3f(u.scale,k/Math.max(1,aspect),k*Math.min(1,aspect),-.7/extent);
  buffers.forEach(function(item){if(!item.count)return;gl.bindBuffer(gl.ARRAY_BUFFER,item.buffer);attrs.forEach(function(a,i){gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,3,gl.FLOAT,false,36,i*12);});gl.drawArrays(gl.TRIANGLES,0,item.count);});
 }
 function update(next){scene=next;var meshes=next.meshes||[],triangles=meshes.reduce(function(sum,m){return sum+(m.faces||[]).length;},0);if(triangles>500000)throw Error('RESOURCE_LIMIT');
  var lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity],present=new Set();
  meshes.forEach(function(m){var key=next.session+':'+m.roi,signature=String(m.geometry_revision)+':'+m.color.join(','),item=buffers.get(key);present.add(key);
   if(!item||item.signature!==signature){if(item)gl.deleteBuffer(item.buffer);var data=new Float32Array((m.faces||[]).length*27),offset=0,rgb=m.color.map(function(v){return v/255;}),v=m.vertices||[],low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity];v.forEach(function(p){for(var j=0;j<3;j++){low[j]=Math.min(low[j],p[j]);high[j]=Math.max(high[j],p[j]);}});
   (m.faces||[]).forEach(function(f){var a=v[f[0]],b=v[f[1]],c=v[f[2]],ab=b.map(function(x,j){return x-a[j];}),ac=c.map(function(x,j){return x-a[j];});
    var n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]],len=Math.hypot.apply(null,n)||1;n=n.map(function(x){return x/len;});
    [a,b,c].forEach(function(p){data.set(p,offset);data.set(n,offset+3);data.set(rgb,offset+6);offset+=9;});
   });
   item={buffer:gl.createBuffer(),count:(m.faces||[]).length*3,signature:signature,low:low,high:high};gl.bindBuffer(gl.ARRAY_BUFFER,item.buffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);buffers.set(key,item);uploads++;
   }
   for(var j=0;j<3;j++){lo[j]=Math.min(lo[j],item.low[j]);hi[j]=Math.max(hi[j],item.high[j]);}
  });
  buffers.forEach(function(item,key){if(!present.has(key)){gl.deleteBuffer(item.buffer);buffers.delete(key);}});
  if(triangles){var nextExtent=Math.max(1,Math.hypot(hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2]));if(count===0||nextExtent>extent*1.15){target=lo.map(function(x,j){return (x+hi[j])/2;});extent=nextExtent;}}
  count=triangles*3;draw();
 }
 function down(e){if(e.button!==0)return;e.preventDefault();drag={x:e.clientX,y:e.clientY,yaw:yaw,pitch:pitch,id:e.pointerId};canvas.setPointerCapture(e.pointerId);}
 function move(e){if(!drag||e.pointerId!==drag.id)return;yaw=drag.yaw+(e.clientX-drag.x)*.008;pitch=drag.pitch+(e.clientY-drag.y)*.008;draw();}
 function up(e){if(drag&&e.pointerId===drag.id){drag=null;try{canvas.releasePointerCapture(e.pointerId);}catch(_){}}}
 function wheel(e){e.preventDefault();zoom=Math.max(.2,Math.min(15,zoom*(e.deltaY<0?1.12:1/1.12)));draw();}
 canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);canvas.addEventListener('wheel',wheel,{passive:false});
 return {update:update,draw:draw,center:function(p){target=p.slice();draw();},fit:function(){count=0;zoom=1;if(scene)update(scene);},dispose:function(){disposed=true;canvas.removeEventListener('pointerdown',down);canvas.removeEventListener('pointermove',move);canvas.removeEventListener('pointerup',up);canvas.removeEventListener('pointercancel',up);canvas.removeEventListener('wheel',wheel);buffers.forEach(function(item){gl.deleteBuffer(item.buffer);});buffers.clear();gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);},get triangles(){return count/3;},get uploads(){return uploads;}};
}
window.RadaiContourScene={create:create};
})();
'''
