// Inspect actual content screenshots and task-specific behavior before passing this review.
// Content changes invalidate old evidence: return to pending and recheck affected states.
// Evidence identifies real screenshots/check results; it is not an aesthetic score from the SDK.
export const review = {
  status: 'passed',
  checks: [
    {
      name: '新角色绑骨与搬运动作多视角',
      status: 'passed',
      evidence: '../review/character_02/rig_rest_front.png、rig_rest_side.png、rig_rest_back.png、carry02_contact_sheet.jpg：实际检查休息姿势及第 1／17／33／49 帧的正面、三分之四、侧面和背面，双手保持前托，左右腿后半周期换边，未见明显衣物或手脚穿插。',
    },
    {
      name: 'GLB 骨架、动画、UV 与贴图回导',
      status: 'passed',
      evidence: '../review/character_02/carry02_glb_structure.json、carry02_glb_roundtrip_report.json：22 个关节，两套动画各 66 通道，4096×4096 主贴图与 UV 完整，无未绑定顶点；首尾矩阵误差为 0，17 个采样点确认换腿，双手位移约 11 毫米。',
    },
    {
      name: '浏览器实际播放与循环定位',
      status: 'passed',
      evidence: '离屏运行实例中 22 根骨骼均存在，17 个采样点得到 16 种腿部世界姿态，后半周期正确换腿；双手世界位移约 10.7 毫米，循环首尾与重复定位矩阵误差均为 0；已查看运行中半周期画面，材质、灯光与构图正常，sceneLint 返回空数组。',
    },
    {
      name: '材质卡与动作速度恢复',
      status: 'passed',
      evidence: '选中角色后材质卡与 asset.getMaterials 均显示“红衣卡通女孩 · 主贴图 · 引用 1”；速度由 1 改为 1.25 后，同一时间腿部矩阵最大差异为 0.177069，恢复为 1 后与基准矩阵逐项完全一致，flush 保存成功，最终 overrides 为空。',
    },
  ],
  limitations: [
    '搬运动作为原地循环，不含根节点位移，不生成搬运道具；基础骨架不含手指、精细表情骨骼和 IK 控制器。穿模检查限于上述关键帧与采样角度。',
  ],
}
