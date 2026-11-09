import * as THREE from 'three'
import { enableToneMapping } from './kit/tonemap.js'
import { bindParams, excludeFromFraming, framingReport } from './kit/edit3d.js'

export async function createScene({ asset }) {
  enableToneMapping({ curve: 'neutral', exposure: 1 })
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#d9dee6')

  const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 50)
  camera.name = '主相机 · 红衣女孩三分之四视角'
  camera.position.set(1.35, 0.88, 2.15)
  camera.lookAt(0, 0.5, 0)
  scene.add(camera)

  const model = await asset.loadModel('/models/red-girl-carry.glb')
  model.object.name = '红衣卡通女孩 · 搬运走路'
  model.object.traverse((object) => {
    if (!object.isMesh) return
    object.castShadow = true
    object.receiveShadow = true
    for (const material of [object.material].flat()) {
      if (!material) continue
      if (!material.name || /^Material(?:\.\d+)?$/.test(material.name)) material.name = '红衣卡通女孩 · 主贴图'
    }
  })
  scene.add(model.object)

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(10, 10),
    new THREE.MeshStandardMaterial({ color: '#b9c0ca', roughness: 0.96, metalness: 0 }),
  )
  ground.name = '棚拍地面'
  ground.material.name = '棚拍地面 · 浅灰哑光'
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.004
  ground.receiveShadow = true
  scene.add(ground)
  excludeFromFraming(ground)

  const ambient = new THREE.HemisphereLight(0xe8f1ff, 0x62584e, 1.5)
  ambient.name = '环境光 · 柔和棚拍'
  const key = new THREE.DirectionalLight(0xffead6, 3.2)
  key.name = '主光 · 左前暖光'
  key.position.set(2.2, 3.8, 3.0)
  key.castShadow = true
  key.shadow.mapSize.set(1024, 1024)
  key.shadow.camera.left = -1.2
  key.shadow.camera.right = 1.2
  key.shadow.camera.top = 1.5
  key.shadow.camera.bottom = -0.5
  key.shadow.camera.near = 0.1
  key.shadow.camera.far = 10
  key.shadow.bias = -0.0004
  const fill = new THREE.DirectionalLight(0xd7e7ff, 0.85)
  fill.name = '补光 · 右侧冷光'
  fill.position.set(-2.5, 1.8, 2.0)
  const rim = new THREE.DirectionalLight(0xe8f1ff, 1.25)
  rim.name = '轮廓光 · 后侧'
  rim.position.set(0.4, 2.8, -2.5)
  scene.add(ambient, key, fill, rim)

  asset.register('character', model.object, { name: '红衣卡通女孩' })
  asset.register('ground', ground, { name: '棚拍地面' })
  asset.register('camera', camera, { name: '主相机' })

  const clip = model.animations.find((item) => item.name.includes('搬运')) || model.animations[0]
  if (!clip) throw new Error('新角色 GLB 中未找到搬运走路动画')
  const mixer = new THREE.AnimationMixer(model.object)
  mixer.clipAction(clip).play()
  const settings = { speed: 1 }
  const unsubscribe = bindParams(asset, 'character_motion', settings, {
    speed: { label: '红衣女孩 · 动作速度', type: 'number', min: 0.25, max: 2, step: 0.05 },
  }, () => {}, { name: '角色动作', objectId: 'character' })

  asset.registerAnimation('carry_walk', {
    name: '搬运走路 · 双手前举',
    objectId: 'character',
    duration: clip.duration,
    sample(time) {
      mixer.setTime((time * settings.speed) % clip.duration)
    },
  })

  const framing = framingReport(scene, model.object)
  console.info('红衣女孩取景检查', framing)

  return {
    scene,
    camera,
    dispose() {
      unsubscribe()
      mixer.stopAllAction()
      mixer.uncacheRoot(model.object)
      scene.traverse((object) => {
        object.geometry?.dispose()
        for (const material of [object.material].flat()) material?.dispose()
      })
    },
  }
}
