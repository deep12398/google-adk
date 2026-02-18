# Step 4: 需求收集 + 品类技能

## 教学目标

- **Phase 05** Skill dataclass + SkillRegistry + SkillAwareToolset + InstructionProvider

## 学到什么

品类技能系统如何为不同产品品类动态注入专业知识。
`requirements_agent` 推断品类后自动激活对应技能，
LLM 获得领域专家级的指令和工具。

## 核心概念

```
Skill          — 可复用的知识包（name + description + instruction + tools）
SkillRegistry  — 技能注册中心，管理技能目录
SkillAwareToolset — BaseToolset 子类，按需动态加载技能工具
InstructionProvider — callable，根据 state 动态生成 system instruction
infer_category — 品类推断工具（规则匹配 categories.json）
```

## 技能包设计

| 品类 | 技能名 | 专业知识内容 |
|------|--------|------------|
| steel | steel_skill | 钢材牌号、表面处理、标准（GB/T, ASTM）、认证 |
| electronics | electronics_skill | 规格参数、合规认证（CE, FCC, RoHS）、PCB 工艺 |
| packaging | packaging_skill | 材质（瓦楞、灰板）、印刷工艺、开窗/覆膜 |

## 创建文件清单

```
新建:
  tools/requirement_tools.py      # infer_category, collect_requirements
  skills/
    __init__.py
    base.py                       # 复用 Phase 05 的 Skill + SkillRegistry
    loader.py                     # 复用 Phase 05 的 SkillAwareToolset + make_skill_instruction
    steel_skill.py
    electronics_skill.py
    packaging_skill.py
  agents/requirements_agent.py
  prompts/
    __init__.py
    templates.py                  # 共享 prompt 模板

修改:
  agents/orchestrator.py          # 添加 requirements_agent
  apps/app.py                     # STEP="4"
```

## 代码实现

### tools/requirement_tools.py

```python
"""需求收集工具——品类推断 + 结构化需求。"""

import json
from pathlib import Path
from google.adk.tools import ToolContext

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> list | dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def infer_category(product_description: str, tool_context: ToolContext) -> dict:
    """Infer product category from a description using the category taxonomy.

    Matches against category names and their aliases in categories.json.
    Sets product_category in state for downstream agents and skill loading.

    Args:
        product_description: The product description to classify.
    """
    categories = _load_json("categories.json")
    desc = product_description.lower()

    matches = []
    for cat_name, cat_info in categories.items():
        aliases = cat_info.get("aliases", [])
        if cat_name in desc or any(a.lower() in desc for a in aliases):
            matches.append({"category": cat_name, "parent": cat_info.get("parent", "")})

    if matches:
        tool_context.state["product_category"] = matches[0]["category"]

    return {
        "product_description": product_description,
        "inferred_categories": matches if matches else [{"category": "unknown", "parent": ""}],
    }


def collect_requirements(
    product_description: str,
    quantity: int = 0,
    quality_standard: str = "",
    budget_range: str = "",
    delivery_deadline: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Collect and structure sourcing requirements from user input.

    Args:
        product_description: What the user needs.
        quantity: Required quantity (0 if unknown).
        quality_standard: Required standard (e.g., ISO9001).
        budget_range: Budget range (e.g., "10000-20000 CNY").
        delivery_deadline: When needed (e.g., "2 weeks").
    """
    reqs = {
        "product": product_description,
        "quantity": quantity,
        "quality": quality_standard,
        "budget": budget_range,
        "deadline": delivery_deadline,
    }
    missing = [k for k, v in reqs.items() if not v]

    if tool_context:
        tool_context.state["requirements"] = reqs
        tool_context.state["temp:missing_fields"] = missing

    return {
        "requirements": reqs,
        "missing_fields": missing,
        "completeness": round((len(reqs) - len(missing)) / len(reqs), 2),
        "suggestion": f"Please also provide: {', '.join(missing)}" if missing else "All requirements collected!",
    }
```

### skills/base.py

直接复用 Phase 05 的 `Skill` + `SkillRegistry`（参考 `phases/05-skills/skills/base.py`）。

### skills/loader.py

直接复用 Phase 05 的 `SkillAwareToolset` + `make_skill_instruction`（参考 `phases/05-skills/skills/loader.py`）。
将 `make_skill_instruction` 的 base prompt 改为采购场景。

### skills/steel_skill.py

```python
"""钢材品类技能——注入钢材采购专业知识。"""

from skills.base import Skill

steel_skill = Skill(
    name="steel",
    description="Steel & metals sourcing expertise (grades, standards, testing).",
    instruction=(
        "## Steel Sourcing Expertise\n\n"
        "When sourcing steel/metals products, apply this domain knowledge:\n\n"
        "**Common Grades:**\n"
        "- Stainless: 201, 304, 316L, 430 (cost increases with grade)\n"
        "- Carbon: Q235, Q345 (by GB/T), A36, SS400 (by ASTM/JIS)\n\n"
        "**Key Specs to Confirm:**\n"
        "- Thickness tolerance (e.g., +/-0.02mm for precision)\n"
        "- Surface finish: 2B, BA, Mirror (#8), Brushed (#4)\n"
        "- Edge: slit edge vs mill edge\n\n"
        "**Standards:** GB/T, ASTM, JIS, EN, AISI\n\n"
        "**Certifications:** ISO9001, Mill Test Certificate (MTC), SGS report\n\n"
        "**MOQ:** Typically 5-10 tons standard, 20+ tons custom\n\n"
        "**Ask the user about:** material grade, thickness, width, finish, edge type.\n"
    ),
    tools=[],  # 钢材技能仅注入知识
)
```

### skills/electronics_skill.py

```python
"""电子品类技能。"""

from skills.base import Skill

electronics_skill = Skill(
    name="electronics",
    description="Electronics sourcing expertise (specs, compliance, components).",
    instruction=(
        "## Electronics Sourcing Expertise\n\n"
        "When sourcing electronics/components:\n\n"
        "**Compliance Certifications:** CE (EU), FCC (US), RoHS, REACH, UL\n"
        "**PCB Specs:** layer count, thickness, copper weight, surface finish (HASL/ENIG)\n"
        "**Component Specs:** voltage, current, operating temperature range\n"
        "**MOQ:** Typically 500-1000 pcs for components, 100+ for assemblies\n\n"
        "**Ask about:** voltage requirements, operating environment, compliance market.\n"
    ),
    tools=[],
)
```

### skills/packaging_skill.py

```python
"""包装品类技能。"""

from skills.base import Skill

packaging_skill = Skill(
    name="packaging",
    description="Packaging sourcing expertise (materials, printing, structure).",
    instruction=(
        "## Packaging Sourcing Expertise\n\n"
        "When sourcing packaging:\n\n"
        "**Materials:** corrugated (E/F/B flute), greyboard, kraft, art paper\n"
        "**Printing:** offset, flexo, digital, hot stamping, UV spot\n"
        "**Finishing:** matte/gloss lamination, emboss, deboss, window patch\n"
        "**Structure:** tuck end, mailer box, rigid box, sleeve\n"
        "**MOQ:** Typically 500-1000 pcs (offset), 100 pcs (digital)\n\n"
        "**Ask about:** box dimensions, material preference, printing colors.\n"
    ),
    tools=[],
)
```

### agents/requirements_agent.py

```python
"""需求收集 Agent——品类推断 + 技能加载。

使用 SkillAwareToolset 实现渐进加载：
  1. LLM 首先看到技能目录（仅 name + description）
  2. 推断品类后调用 activate_skill → 加载完整指令
  3. 后续 LLM 请求自动获得领域专业知识
"""

from google.adk.agents.llm_agent import LlmAgent
from skills.base import SkillRegistry
from skills.loader import SkillAwareToolset, make_skill_instruction
from skills.steel_skill import steel_skill
from skills.electronics_skill import electronics_skill
from skills.packaging_skill import packaging_skill
from tools.requirement_tools import infer_category, collect_requirements

# 注册所有品类技能
registry = SkillRegistry([steel_skill, electronics_skill, packaging_skill])

requirements_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="requirements_agent",
    description="Collects sourcing requirements, infers category, loads domain expertise.",
    instruction=make_skill_instruction(registry),  # callable InstructionProvider
    tools=[infer_category, collect_requirements, SkillAwareToolset(registry)],
    output_key="requirements_summary",
)
```

### orchestrator.py 修改

添加 requirements_agent 到 sub_agents，更新路由规则。

## 验证

```bash
cd phases/09-capstone

# 钢材品类 → 技能加载
STEP=4 PROMPT="I need 304 stainless steel sheets, 1mm thick, 500 tons, ISO9001" python apps/main.py
# 期望：infer_category→steel → activate_skill("steel") → 专业知识注入

# 电子品类
STEP=4 PROMPT="I need PCB boards for IoT devices" python apps/main.py
# 期望：infer_category→electronics → 电子技能

# 需求不完整
STEP=4 PROMPT="I need some packaging boxes" python apps/main.py
# 期望：collect_requirements → 提示补充 quantity, quality 等
```

## Prompt 设计原则（所有 Step 通用）

**自适应用户专业程度：** Skill instruction 必须包含 `Adapt to User's Expertise Level` 段落，
根据用户措辞自动判断 PROFESSIONAL / CASUAL / MIXED，采取不同对话策略：

- **PROFESSIONAL** — 用户提到具体参数/术语 → 直接收下，只补问业务信息（数量/预算/交期）
- **CASUAL** — 用户只描述用途/场景 → 先问场景，根据场景推荐规格并用大白话解释
- **MIXED** — 用户提供部分参数 → 收下已有信息，根据场景推断缺失规格，确认推荐

**核心理念：** Skill 里的知识用来帮用户做决策，不是用来考用户的。
`collect_requirements` 用在对话结束后结构化存储，不用来驱动追问。

## 你应该理解的

1. `Skill` 是独立于 Agent 的知识包，可被不同 Agent 加载
2. `SkillAwareToolset.get_tools()` 在每次 LLM 调用前被 ADK 调用 → 动态返回工具
3. `make_skill_instruction` 返回 callable → ADK 每次 LLM 调用前执行 → 动态生成 instruction
4. 未激活技能时只占 ~100 tokens（目录），激活后才加载完整指令
5. `infer_category` 写入 `state["product_category"]`，供技能系统和搜索 Agent 使用
6. Skill instruction 必须自适应用户专业程度（PROFESSIONAL / CASUAL / MIXED）
