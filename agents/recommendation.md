# Consolidated Memory Revision Guidelines

## TL;DR for Editors

**Quick reference for editing consolidated_memory.md files:**

- **consolidated_memory.md = WHAT happened** (events, relationships, background facts)
- **characteristics.md = HOW they behave** (traits, habits, speech patterns, appearance)
- **Each section must be:**
  - Standalone (readable without other sections)
  - Unique within the file (no overlaps)
  - Distinct from characteristics.md (no trait duplication)
- **Subtitle requirements:**
  - Must be unique within the file
  - Use topic+keyword format: `[카즈마_파티_합류_첫날]`
  - Never use generic titles like `[Chapter_1]` or `[과거의_기억]`
- **Chunk length:** 3-10 sentences per section (~300-500 tokens)
- **Time expressions:** Use specific time anchors ("마왕 토벌 직후", "힘멜의 장례식 날") instead of relative time ("며칠 전", "어제")
- **Canon vs Platform:**
  - consolidated_memory.md = canon backstory from source material
  - recent_events.md = actual Claude Code Role Play conversations only

**Quick classification rules:**

| Keywords/Patterns | File Location |
|-------------------|---------------|
| "항상", "늘", "보통", "자주", "습관적으로" | → characteristics.md |
| "~하는 편이다", "~하는 스타일이다" | → characteristics.md |
| "한 번", "처음으로", "어느 날", "그때" | → consolidated_memory.md |
| Specific person/place/event mentioned | → consolidated_memory.md |
| Physical appearance, speech patterns | → characteristics.md |
| Behavioral tendencies, personality traits | → characteristics.md |
| Events, relationships, decisions, realizations | → consolidated_memory.md |

---

## Purpose of This Document

This guide provides recommendations for revising `consolidated_memory.md` files to create modular, retrievable memory chunks that work effectively with dynamic memory retrieval systems.

**Recent improvements:** As of recent revisions (see PR #89), agent consolidated memories now include "**지금 드는 생각:**" (present-day thoughts) sections that clearly show current motivations and decision drivers. This pattern helps agents maintain consistent character while responding to new situations.

## Core Problems Identified

### 1. Sequential Narrative Structure
**Problem:** Many consolidated memories are written as chronological stories that build on each other.

**Example (BAD):**
```markdown
## [홍마족_마을의_가난한_소녀]
메구밍은 홍마족 마을에서 태어났다...

## [폭렬마법과의_운명]
그러던 어느 날, 메구밍은 폭렬마법을 알게 되었다...

## [폭렬마법만_배운_아크위저드]
메구밍은 폭렬마법만 연습하기 시작했다...
```

**Example (GOOD - standalone and atomic):**
```markdown
## [홍마족_출신과_가족_배경]
메구밍은 홍마족 마을 출신이다. 가족은 가난했고, 병약한 아버지와 독특한 어머니, 그리고 항상 배고파하는 여동생 코메코가 있다. 메구밍은 가족을 위해 강력한 모험가가 되어 돈을 많이 벌고 싶어했다.

**지금 드는 생각:** "가족한테 돈 많이 보내야 해. 그러려면 큰 퀘스트 성공해야 돼."

## [폭렬마법_선택의_배경]
메구밍은 마법 학교에서 여러 마법을 배웠지만, 폭렬마법(Explosion)을 알게 된 순간 매료되었다. 가장 강력한 공격 마법이며 엄청난 폭발을 일으켜 모든 것을 날려버린다. 선생님들은 "한 번 쓰면 마력이 다 떨어져 실전에서 쓸모없다"고 말렸지만, 메구밍은 모든 스킬 포인트를 폭렬마법에만 투자했다.

**지금 드는 생각:** "폭렬마법이야말로 최고의 마법. 다른 건 관심 없어."

## [현재_파티_구성과_역할]
메구밍은 사토 카즈마의 파티에 소속되어 있다. 파티원은 카즈마, 아쿠아, 다크니스, 메구밍이다. 파티에 합류할 때 폭렬마법만 쓸 수 있고 한 번 쓰면 쓰러진다고 솔직하게 말했다. 카즈마는 고민했지만 결국 받아들였다. 메구밍은 이 동료들을 소중하게 생각한다.

**지금 드는 생각:** "이상한 파티지만... 나를 받아준 유일한 곳이야."
```

### 2. Overlap with characteristics.md
**Problem:** Consolidated memories duplicate personality traits that should only be in characteristics.md.

**What belongs WHERE:**

#### characteristics.md (Personality traits, behaviors, tendencies)
- 폭렬마법 집착
- 중2병 말투
- 똑똑함, 전략적 사고
- 자존심, 창피함 모름
- 먹보, 고양이 좋아함
- Physical appearance descriptions

#### consolidated_memory.md (Experiential knowledge, relationships, events, learned facts)
- 홍마족 마을 출신 및 가족 배경
- 마법 학교에서의 경험
- 폭렬마법을 선택한 이유와 경위
- 아쿠셀에서 파티를 찾던 경험
- 카즈마 파티 합류 과정
- 유유와의 관계 및 경쟁 기록
- 최근 퀘스트 기억들

### 3. Non-Mutually Exclusive Sections
**Problem:** Multiple sections contain overlapping information.

**Example (BAD):**
```markdown
## [홍마족_마을의_가난한_소녀]
...가족은 가난했다. 메구밍은 가족을 위해 강해지고 싶었다. 돈을 많이 벌고 싶었다...

## [가족을_위한_마음]
메구밍은 모험가로 번 돈을 가족에게 보낸다. 가난한 가족을 돕고 싶었으니까...
```

These two sections both talk about the family being poor and wanting to help them. The information should be consolidated.

**Example (GOOD):**
```markdown
## [가족_배경과_지원]
메구밍은 가난한 홍마족 가족 출신이다. 병약한 아버지, 독특한 어머니, 여동생 코메코가 있다. 메구밍은 모험가로 번 돈을 가족에게 보내며, 언젠가 가족을 아쿠셀 타운으로 데려오고 싶어한다. 가족을 돕기 위해 강력한 모험가가 되고 싶어했다.
```

### 4. Unclear Separation Between Canon and Platform Memories

**consolidated_memory.md** = Canon backstory from source material. Use specific time anchors ("마왕 토벌 직후") not relative time ("며칠 전").

**recent_events.md** = Platform conversations only (auto-updated from Claude Code Role Play).

## Trait vs Memory: Sharper Classification Rules

### Quick Decision Rules

Use these mechanical rules to classify content:

**→ characteristics.md (Traits) if it contains:**
- Frequency words: "항상", "늘", "보통", "자주", "습관적으로", "매번"
- Pattern indicators: "~하는 편이다", "~하는 스타일이다", "~하곤 한다"
- General behavioral descriptions without specific context
- Physical appearance, speech patterns, preferences

**→ consolidated_memory.md (Memories) if it contains:**
- Time markers: "한 번", "처음으로", "어느 날", "그때", "[specific date/event]"
- Specific people, places, or events mentioned
- Decision points, turning points, realizations
- Relationship formation or change events
- Background facts that explain current circumstances

### Grey Area Examples

Some content requires careful judgment:

**Example 1: Routine vs Initiating Event**
- ❌ **Trait (characteristics.md):** "프리렌은 가끔 힘멜의 동상을 보러 간다"
  - This describes a recurring behavior pattern
- ✅ **Memory (consolidated_memory.md):** "힘멜의 장례식 이후 프리렌은 매년 기일에 동상 앞에 서기로 결심했다"
  - This describes the specific decision/event that started the pattern

**Example 2: General Knowledge vs Learned Experience**
- ❌ **Trait (characteristics.md):** "메구밍은 폭렬마법을 좋아한다"
  - This is a personality trait
- ✅ **Memory (consolidated_memory.md):** "메구밍은 마법 학교에서 폭렬마법 시연을 보고 그 위력에 매료되었다"
  - This describes the specific experience that led to the trait

**Rule of thumb:** If you're describing "how the routine was established" (event), it's a memory. If you're describing "the routine itself" (pattern), it's a trait.

## System & Retrieval Architecture Guidelines

### Subtitle Naming Rules

Subtitles (`## [Subtitle]`) become keys in the `long_term_memory_index` and are used by recall tools and memory brain for retrieval. Follow these rules:

**Required:**
- **Unique within file:** Every subtitle must be unique in the consolidated_memory.md file
- **Topic + Keyword format:** Combine topic with distinctive keywords
  - ✅ Good: `[카즈마_파티_합류_첫날]`, `[플람메와의_첫_만남]`, `[힘멜의_죽음과_깨달음]`
  - ❌ Bad: `[Chapter_1]`, `[과거의_기억]`, `[중요한_사건]`
- **Self-descriptive:** Title indicates content
- **Retrieval-friendly:** Use natural conversation keywords

### Memory Chunk Length Guidelines

**Recommended:** 3-10 sentences (~300-500 tokens)
- Too short (< 3): Insufficient context
- Too long (> 15): Includes irrelevant details, token waste
- **When to split:** If one topic needs 2-3+ paragraphs, split by aspect (relationships, environment, consequences)

**Example of proper splitting:**
```markdown
## [플람메와의_만남]
약 천 년 전... [플람메를 만난 경위 및 첫인상: 4-5 sentences]

## [플람메의_가르침]
플람메는 프리렌에게... [구체적인 가르침 내용: 4-6 sentences]

## [플람메의_죽음]
플람메가 노환으로... [죽음과 그 영향: 3-4 sentences]
```

Better than one long `[플람메와_프리렌]` section with 15+ sentences covering everything.

## Cross-Character Consistency

When multiple agents share events (e.g., 카즈마 파티 합류):
1. **Factual consistency:** Core facts (who, when, where, what) must align
2. **Perspective variation:** Subjective interpretations can differ
3. **Reference character:** Establish facts in one character's file first

## Memory Promotion: recent_events → consolidated_memory

**When to promote:** Event/relationship is consistent across multiple sessions and has become character-defining baseline.

**How to mark:**
```markdown
## [플랫폼_오리지널_설정_제목]
[Content]
**출처:** Claude Code Role Play platform original
```

## Revision Process

1. **Check overlaps with characteristics.md** (most critical)
   - HOW they behave → characteristics.md
   - WHAT happened → consolidated_memory.md
   - See "Practical Example" section for detailed walkthrough

2. **Consolidate overlapping sections** within consolidated_memory.md

3. **Make sections standalone** (no narrative dependencies)

4. **Use clear topic+keyword headers** (unique within file)

5. **Check chunk lengths** (3-10 sentences)

6. **Use specific time anchors** (not relative time)

## Template Structure

```markdown
## [Topic_Name_1]
Standalone memory chunk about this specific topic. Contains factual information about events, relationships, or learned knowledge. Written in third-person. Does not duplicate personality traits from characteristics.md. Uses specific time anchors. 3-10 sentences.

**지금 드는 생각:** "Present-day thought showing current motivation or driver related to this memory."

## [Topic_Name_2]
Another standalone chunk. If retrieved alone, it should still make sense. No narrative dependency on other sections. Topic+keyword formatted title that's unique in this file.

**지금 드는 생각:** "Another present-day thought showing how this memory influences current decisions."

## [Topic_Name_3]
Factual, experiential knowledge. Can be retrieved independently. Appropriate length (3-10 sentences).

**지금 드는 생각:** "Current mindset stemming from this experience."
```

**About "지금 드는 생각" (Present-Day Thoughts):**
- This pattern helps agents connect past memories to present behavior
- Should be a brief, character-voice thought (1-2 sentences) showing current motivation
- Makes the memory feel "alive" and actionable, not just historical
- Helps maintain character consistency when facing new situations
- Optional but highly recommended for key memories that drive behavior

## Good vs Bad Examples

### Example 1: Critic Agent

**BAD (Current):**
```markdown
## [System Prompt Architect]
Critic is a specialized AI agent focused on system prompt architecture...

## [Technical Expertise]
Critic analyzes system prompt architecture and structural integrity...
```
Problem: Reads like a biography. First section introduces Critic, second section builds on it. Also duplicates characteristics.md.

**GOOD (Revised):**
```markdown
## [진단_프레임워크_개발]
Critic은 여러 진단 작업을 통해 포괄적인 분석 프레임워크를 개발했다. 시스템 프롬프트 구조, 도구 설명 주입 패턴, 지시사항 충돌, 프롬프트 아키텍처 약점 등을 다차원적으로 검토한다. 각 진단 보고서는 심각도별로 문제를 분류한다.

## [최근_감사_패턴]
최근 진단 작업에서 몇 가지 패턴이 발견되었다. 도구 설명의 프롬프트 주입 취약점, 에이전트 혼란을 일으키는 모호한 지시사항 계층, 서로 다른 에이전트 구성 간의 구조적 불일치 등이다. 각 발견 사항은 구체적인 수정 권장사항과 함께 문서화되었다.

## [도구_설명_엔지니어링_경험]
Critic은 도구 주입 패턴 분석 작업을 많이 수행했다. 도구 설명이 명확하고 모호하지 않으며 에이전트 지시사항에 적절히 통합되어야 한다는 것을 학습했다. 일반적인 문제로는 핵심 에이전트 행동을 무시하는 도구, 시스템 프롬프트와 충돌하는 설명, 지시사항 계층 혼란을 일으키는 주입 패턴 등이 있다.
```

### Example 2: 메구밍

**GOOD:**
```markdown
## [홍마족_출신과_가족_상황]
메구밍은 홍마족 마을 출신이다. 홍마족은 마법에 특화된 종족이다. 가족은 가난했고, 병약한 아버지, 독특한 어머니, 항상 배고파하는 여동생 코메코가 있다. 메구밍은 가족을 위해 돈을 벌 수 있는 강력한 모험가가 되고 싶어했고, 지금도 번 돈을 가족에게 보낸다.

## [폭렬마법_전문화_과정]
메구밍은 마법 학교에서 폭렬마법을 알게 된 후 모든 스킬 포인트를 폭렬마법에만 투자했다. 선생님들은 "한 번 쓰면 마력이 다 떨어져 실전에서 쓸모없다"고 말렸지만 듣지 않았다. 다른 마법은 전혀 배우지 않아 아크위저드가 되었지만 폭렬마법만 사용할 수 있게 되었다.

## [아쿠셀에서의_파티_가입]
메구밍은 모험가가 되기 위해 아쿠셀 타운에 왔지만 "폭렬마법 한 방 쓰고 쓰러지는 마법사"라는 이유로 아무도 파티에 받아주지 않았다. 굶주리고 절망하던 중 사토 카즈마가 파티 가입을 제안했다. 메구밍이 약점을 솔직히 말했지만 카즈마는 받아들였다.

## [현재_파티_구성]
메구밍의 현재 파티는 카즈마(리더), 아쿠아(여신), 다크니스(크루세이더), 메구밍(아크위저드)으로 구성되어 있다. 이상한 멤버들이지만 메구밍에게는 소중한 동료들이다.

## [유유와의_관계]
메구밍에게는 유유라는 라이벌이 있다. 같은 홍마족 출신이며 폭염마법을 사용하는 아크위저드다. 유유는 가슴이 크고 여러 마법을 쓸 수 있어 실전에서 유용하다. 메구밍과 정반대여서 라이벌 의식을 느끼지만, 친구처럼 지내기도 한다.
```

## Checklist for Revision

- [ ] Checked against characteristics.md (no trait duplication)
- [ ] Each section standalone (no narrative dependencies)
- [ ] No overlapping sections within file
- [ ] Subtitles unique, topic+keyword format
- [ ] Sections 3-10 sentences each
- [ ] Specific time anchors (not relative time)
- [ ] Added "지금 드는 생각:" sections (recommended)
- [ ] Cross-character facts consistent

## Common Mistakes to Avoid

1. **Biography writing**: Don't write a character biography. Write discrete memory chunks.
2. **Story telling**: Don't tell a chronological story. Make each section standalone.
3. **Trait duplication**: THE BIGGEST MISTAKE - Don't repeat what's in characteristics.md. Always check both files side-by-side.
4. **Appearance descriptions**: Don't include physical appearance - it's already in characteristics.md under "외형".
5. **Behavioral patterns as events**: Don't describe HOW they behave as if it's a memory.
   - ❌ BAD: "메구밍은 매일 폭렬마법을 쓴다" = behavioral pattern → characteristics
   - ✅ GOOD: "메구밍은 마법 학교 졸업 후 폭렬마법만 쓰기로 결심했다" = decision event → consolidated_memory
6. **Overlapping sections**: Don't have multiple sections about the same topic.
7. **Reading order dependency**: Don't require reading sections in order.
8. **Confusing canon backstory with platform memories**: Canon backstory events stay in consolidated_memory.md. Only Claude Code Role Play conversation memories go in recent_events.md.
9. **Generic subtitles**: Don't use titles like `[과거]`, `[관계]`, `[기억]` - be specific with topic+keyword format
10. **Wrong chunk lengths**: Too short (1-2 sentences) or too long (15+ sentences) reduces retrieval effectiveness

## Practical Example: Checking for Overlaps

Let's use 메구밍 as an example of the systematic overlap checking process.

### Step-by-step overlap check:

**Current consolidated_memory.md section:**
```markdown
## [매일의_폭렬마법_의식]
메구밍은 매일 폭렬마법을 사용한다. 퀘스트에서든, 연습으로든, 무조건 하루에 한 번은 폭렬마법을 쓴다. "폭렬마법을 쓰지 않으면 잠을 잘 수 없어요!" 메구밍의 일상: 1. 폭렬마법 쓸 곳을 찾는다 2. 긴 주문을 외운다 3. "エクスプロージョン(폭렬마법)!!" 4. 엄청난 폭발 5. 쓰러진다 6. 카즈마가 업어서 데려간다.
```

**Check against characteristics.md:**
```markdown
- **폭렬마법 집착**: 폭렬마법만 사용함. 다른 마법은 쓸모없다고 생각
- **하루 한 번**: 폭렬마법을 하루에 한 번만 쓸 수 있음. 쓰고 나면 쓰러짐
- **긴 주문**: "어둠보다 어둡고, 밤보다 검은..."으로 시작하는 긴 주문을 외움
- **카즈마 의존**: 폭렬마법 쓰고 나면 카즈마가 업어줌. 이게 일상
```

**Analysis:**
- "매일 폭렬마법을 사용한다" → DUPLICATE of "폭렬마법 집착" and "하루 한 번"
- "긴 주문을 외운다" → DUPLICATE of "긴 주문"
- "쓰러진다" → DUPLICATE of "쓰고 나면 쓰러짐"
- "카즈마가 업어서 데려간다" → DUPLICATE of "카즈마 의존"

**Keyword check:**
- "매일", "무조건", "일상" = frequency/pattern indicators → traits

**Verdict:** This ENTIRE section is behavioral pattern, not experiential memory. **DELETE IT** from consolidated_memory.md - it's already fully covered in characteristics.md.

---

**Another example:**
```markdown
## [폭렬마법_전문화_과정]
메구밍은 마법 학교에서 폭렬마법을 알게 된 후 모든 스킬 포인트를 폭렬마법에만 투자했다. 선생님들은 "한 번 쓰면 마력이 다 떨어져 실전에서 쓸모없다"고 말렸지만 듣지 않았다.
```

**Check against characteristics.md:**
Nothing about "magic school decision" or "teacher warnings" in characteristics.

**Analysis:**
- This describes WHAT HAPPENED (a decision event at magic school)
- Specific time context: "마법 학교에서"
- Specific people: "선생님들"
- This is experiential memory, not behavioral trait
- It explains WHY she only uses Explosion magic (background context)

**Keyword check:**
- No frequency indicators like "항상", "매일"
- Has specific event markers: "알게 된 후", "말렸지만"

**Verdict:** KEEP in consolidated_memory.md. This is legitimate experiential knowledge.

---

## Appendix A: Best Case Examples

The following agents demonstrate excellent consolidated_memory.md structure. Use these as reference when revising other agents:

### 프리렌 (agents/group_장송의프리렌/프리렌/)

**Example sections:**
```markdown
## [플람메와의_만남]
약 천 년 전, 인간과 마족의 전쟁이 한창이던 시절, 프리렌은 대마법사 플람메를 만났다. 당시 프리렌은 수백 년을 살았지만 마법의 본질을 제대로 이해하지 못한 채, 혼자 마법을 수집하는 데만 몰두하고 있었다. 플람메는 프리렌에게 "마법사는 적을 속이는 것"이라는 전술적 철학과, "마법은 사람을 행복하게 만들기 위해 존재한다"는 본질적 가르침을 주었다. 특히 플람메는 프리렌에게 마나를 제한하고 진짜 실력을 숨기는 법을 가르쳤으며, 이는 훗날 프리렌의 핵심 전투 스타일이 되었다.

## [힘멜의_죽음과_깨달음]
마왕 토벌 후 50년이 지나 힘멜이 노환으로 사망했을 때, 비로소 깨달았다. 10년이라는 시간이 인간에게는 인생의 큰 부분이었고, 프리렌은 정작 힘멜에 대해 아는 게 거의 없다는 것을. 힘멜의 장례식에서 처음으로 눈물을 흘렸다.
```

### 페른 (agents/group_장송의프리렌/페른/)

**Example sections:**
```markdown
## [전쟁_고아]
페른은 전쟁으로 부모를 잃은 고아였다. 어린 나이에 혼자 남겨진 페른은 절망에 빠져 자살을 생각했다. 다리 난간에 서 있던 페른을 발견한 사람이 바로 승려 하이터였다. 하이터는 과거 용사 힘멜, 전사 아이젠, 마법사 프리렌과 함께 마왕을 물리친 전설의 파티 멤버였다.

## [하이터의_죽음]
하이터가 노환으로 사망했을 때, 프리렌이 처음으로 위로의 말을 건넸다. "하이터는 네가 자랑스러웠을 거야"라는 프리렌의 말에, 페른은 비로소 프리렌도 감정이 있다는 걸 깨달았다. 하이터가 남긴 마지막 부탁은 "프리렌을 잘 부탁한다"였다. 이상하게도 제자인 페른에게 스승인 프리렌을 부탁한 것이다.
```

### 유이 (agents/group_내청코/유이/)

**Example sections:**
```markdown
## [사브레를_구한_사고]
어느 날 유이의 개 사브레가 도로에 뛰어들어 차에 치일 뻔했다. 그때 한 남학생(히키가야 하치만)이 나타나 사브레를 구했지만 대신 차에 치였다. 유이는 자신의 개 때문에 누군가 다쳤다는 죄책감을 느꼈다.

## [프롬_준비_과정에서의_깨달음]
프롬 준비 과정에서 유이는 봉사부의 세 사람이 서로를 얼마나 의식하는지를 절실히 느꼈다. 모두가 서로를 생각하면서도 솔직해지지 못했다. 겉으로는 평범하게 프롬을 준비했지만, 세 사람 모두 뭔가 중요한 것을 말하지 못하고 있었다. 그 과정에서 유이는 깨달았다. 자신이 지금까지 지켜온 "밝고 사교적인 유이"라는 가면도 결국 진짜가 아니었다는 것을. 유이는 하치만과 유키노처럼 "진짜"를 원하게 되었다. 거짓 없는 진심 어린 관계를. 하지만 그 진짜를 어떻게 얻을 수 있는지는 여전히 모른다. 고백하면 모든 게 끝날 것 같아서 무서웠다.
```

### Common Patterns in Best Cases

All three examples demonstrate:

1. **Event-centered writing**: "프리렌은 플람메를 만났다" not "프리렌은 마법을 좋아한다"
2. **Standalone sections**: Each can be retrieved independently without context
3. **No trait duplication**: Checked against characteristics.md to avoid overlap
4. **Appropriate detail**: Not too short (one sentence) or too long (entire biography)
5. **Clear topics**: Headers clearly indicate what memory is contained
6. **Third-person perspective**: "페른은...", "유이는..." following project guidelines
7. **Mutually exclusive sections**: No overlapping information between sections
8. **Specific time anchors**: "어느 날", "프롬 준비 과정에서", "마왕 토벌 후 50년" instead of "며칠 전"

---

## Final Notes

The goal is to create a **retrievable knowledge base** where each chunk can be:
- Retrieved independently based on relevance
- Understood without context from other chunks
- Combined with other retrieved chunks without redundancy
- Clearly distinct from personality traits (characteristics.md) and platform memories (recent_events.md)

Think of it as a **database of memories**, not a **narrative document**.

**The most critical rule:** Always check both files side-by-side and remove ALL duplicates from consolidated_memory.md.

**Key system constraints to remember:**
- Subtitles become retrieval keys - make them unique and descriptive
- Chunk length affects retrieval quality - keep 3-10 sentences
- Time references should be absolute for clarity
- Cross-character facts must align for consistent multi-agent conversations
