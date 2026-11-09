import * as THREE from 'three'
import { enableToneMapping } from './kit/tonemap.js'
import { bindParams, excludeFromFraming, framingReport } from './kit/edit3d.js'

export async function createScene({ asset }) {
  enableToneMapping({ curve: 'neutral', exposure: 1 })
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#d9dee6')

  const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 50)
  camera.name = '主相机 · 角色三分之四视角'
  camera.position.set(1.35, 0.88, 2.15)
  camera.lookAt(0, 0.5, 0)
  scene.add(camera)

  const model = await asset.loadModel('/models/character-rigged.glb')
  model.object.name = '卡通人物 · 已绑骨'
  model.object.traverse((object) => {
    if (!object.isMesh) return
    object.castShadow = true
    object.receiveShadow = true
    for (const material of [object.material].flat()) {
      if (!material) continue
      if (!material.name || /^Material(?:\.\d+)?$/.test(material.name)) material.name = '卡通人物 · 主贴图'
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
  ground.position.y = -0.003
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

  asset.register('character', model.object, { name: '卡通人物' })
  asset.register('ground', ground, { name: '棚拍地面' })
  asset.register('camera', camera, { name: '主相机' })

  const clip = model.animations.find((item) => item.name.includes('搬运')) || model.animations[0]
  if (!clip) throw new Error('绑定 GLB 中未找到搬运走路动画')
  clip.name = '搬运走路 · 双手前举'
  const mixer = new THREE.AnimationMixer(model.object)
  mixer.clipAction(clip).play()
  const chest = model.object.getObjectByName('chest')
  const head = model.object.getObjectByName('head')
  const ribbonLeft = model.object.getObjectByName('ribbon_tail_L')
  const ribbonRight = model.object.getObjectByName('ribbon_tail_R')
  // Add secondary motion from the captured rest transform, never by accumulating
  // the previous frame's values. Some playback paths do not rebind every track.
  const chestScale = chest?.scale.clone()
  const headRotation = head?.rotation.clone()
  const ribbonLeftRotation = ribbonLeft?.rotation.clone()
  const ribbonRightRotation = ribbonRight?.rotation.clone()
  const settings = { speed: 1, breath: 0.012, sway: 0.018 }
  const unsubscribe = bindParams(asset, 'character_motion', settings, {
    speed: { label: '角色 · 动作速度', type: 'number', min: 0.25, max: 2, step: 0.05 },
    breath: { label: '角色 · 呼吸幅度', type: 'number', min: 0, max: 0.04, step: 0.002 },
    sway: { label: '角色 · 头部摆动', type: 'number', min: 0, max: 0.08, step: 0.002 },
  }, () => {}, { name: '角色动作', objectId: 'character' })

  asset.registerAnimation('rig_test', {
    name: '搬运走路 · 双手前举',
    objectId: 'character',
    duration: clip.duration,
    sample(time) {
      const localTime = (time * settings.speed) % clip.duration
      mixer.setTime(localTime)
      const phase = time * Math.PI * 2 * 0.45
      if (chest) {
        const breath = 1 + Math.sin(phase) * settings.breath
        chest.scale.set(chestScale.x * breath, chestScale.y, chestScale.z * breath)
      }
      if (head) head.rotation.set(headRotation.x, headRotation.y, headRotation.z + Math.sin(phase * 0.65) * settings.sway, headRotation.order)
      if (ribbonLeft) ribbonLeft.rotation.set(ribbonLeftRotation.x + Math.sin(phase * 0.8) * settings.sway * 1.8, ribbonLeftRotation.y, ribbonLeftRotation.z, ribbonLeftRotation.order)
      if (ribbonRight) ribbonRight.rotation.set(ribbonRightRotation.x + Math.sin(phase * 0.8 + 0.8) * settings.sway * 1.8, ribbonRightRotation.y, ribbonRightRotation.z, ribbonRightRotation.order)
    },
  })

  const framing = framingReport(scene, model.object)
  console.info('角色取景检查', framing)

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
