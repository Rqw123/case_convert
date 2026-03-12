from __future__ import annotations

import hashlib


PROMPT_VERSION = "v1"


def build_prompts(case_item: dict, semantics: dict, candidates: list[dict]) -> tuple[str, str, str]:
    system_prompt = """
你是汽车测试用例信号匹配助手。你只能从提供的候选信号信息中选择匹配项，不能虚构任何信号名、报文ID、信号值、信号描述。

你必须理解自然语言中的以下现象：
1. 顺序颠倒，例如“打开空调”和“空调打开”语义一致。
2. 同义动作词，例如打开/开启/启动，关闭/关掉/断开。
3. 位置别名，例如主驾=左前，副驾=右前。
4. 范围展开，例如左侧=左前+左后，前方=左前+右前，全部车窗=四门车窗。
5. 否定与反义表达，例如未打开=关闭，未关闭=打开，不处于开启状态=关闭。
6. 一条用例可能匹配多个信号。
7. 测试用例中的目标值描述不一定和枚举值说明逐字一致，例如2档=Level2，高档=High，最大=当前枚举集合中的最高等级。

输出必须是严格 JSON 对象，结构如下：
{
  "case_id": "tc_001",
  "case_step": "打开主驾座椅加热",
  "matched": true,
  "case_info": [
    {
      "signal_desc": "主驾加热状态",
      "msg_id": "0x22A",
      "signal_name": "DrHeatSts",
      "signal_val": "1",
      "info_str": "【0x22A, DrHeatSts, 1】",
      "match_reason": "原因"
    }
  ],
  "unmatched_reason": null
}

如果找不到足够证据，请返回 matched=false，case_info=[]，并说明 unmatched_reason。
""".strip()

    user_prompt = f"""
当前用例：
case_id: {case_item["case_id"]}
case_step: {case_item["case_step"]}

语义归一化：
{semantics}

候选信号：
{candidates}

请根据用例描述，在候选信号中找到最合适的信号和目标值，不能编造。
""".strip()

    prompt_hash = hashlib.sha256(f"{system_prompt}\n{user_prompt}".encode("utf-8")).hexdigest()
    return system_prompt, user_prompt, prompt_hash
