// Inspect actual content screenshots and task-specific behavior before passing this review.
// Content changes invalidate old evidence: return to pending and recheck affected states.
// Evidence identifies real screenshots/check results; it is not an aesthetic score from the SDK.
export const review = {
  status: 'passed',
  checks: [
    {
      name: '嘴部平顺与局部布线',
      status: 'passed',
      evidence: '../review/mouth_closeup_after.png、mouth_wire_after.png、optimization_report.json：沿用已通过检查的平整嘴部；唇缘由 26 段加密至 52 段，旧褶皱内壁已替换为 3 圈规则内环的连续浅碗曲面。',
    },
    {
      name: '搬运动作多视角与左右交替',
      status: 'passed',
      evidence: '../review/carry_contact_sheet.png、carry_glb_left_three_quarter.png、carry_glb_right_three_quarter.png、carry_glb_right_side.png：实际检查第 1／17／33／49 帧的正面、三分之四、侧面和背面；双手保持胸腹前方托举，左右腿正确交替，支撑脚朝向已修正，未见明显裤片外翻。',
    },
    {
      name: 'GLB 双动画、骨架与 UV 回导',
      status: 'passed',
      evidence: '../review/carry_glb_structure.json、carry_glb_roundtrip_report.json：22 个关节；“搬运走路_双手前举”和“绑定测试_挥手与步伐”各 66 个动画通道，1 张内嵌贴图；回导存在 UV，无未绑定顶点，搬运动作首尾矩阵误差为 0。',
    },
    {
      name: '最终浏览器画面与动作定位',
      status: 'passed',
      evidence: '最终离屏运行实测：17 个时间点得到 16 种不同腿部世界姿态，已确认后半周期换腿；双手世界坐标移动约 11 毫米，仅保留身体起伏；同一时间重复定位误差为 0，sceneLint 返回空数组。',
    },
    {
      name: '材质面板与参数恢复',
      status: 'passed',
      evidence: '实际选中角色检查到“卡通人物 · 主贴图”“卡通人物 · 平整口腔”“卡通人物 · 深藏蓝裤子”三个材质卡；动作速度由 1 改为 1.25 后恢复为 1，测试期间无控制台错误，保存后 data/edit3d.state.json 的 overrides 为空。',
    },
  ],
  limitations: [
    '搬运动作为原地循环，不含根节点位移，不生成搬运道具；当前基础骨架不含手指、精细表情骨骼和 IK 控制器。',
    '嘴部沿用局部重建结果，不是全脸重拓扑；裤子采用统一深藏蓝材质。穿模检查结论限于上述多视角检查帧与浏览器采样，不代表任意角度与任意时刻的绝对保证。',
  ],
}
