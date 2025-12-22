# Judge Evaluation Criteria

This document describes how the Judge agent evaluates follow-up questions in a blind comparison.

## Evaluation Setup

The Judge receives:
1. **Interview context** - Previous Q&A exchanges from the transcript
2. **Current answer** - The interviewee's most recent response
3. **Question A** - One of the two questions (randomly ordered)
4. **Question B** - The other question (randomly ordered)

The Judge does NOT know which question is from Jane and which is the original interviewer question.

## Evaluation Criteria

Questions are evaluated on four dimensions:

### 1. Relevance to the Answer
- Does the question directly respond to what the interviewee just said?
- Does it pick up on specific details or themes from their answer?
- Does it ignore important points the interviewee raised?

### 2. Depth and Thoughtfulness
- Does the question probe deeper into the topic?
- Does it encourage reflection rather than surface-level responses?
- Does it show understanding of the subject matter?

### 3. Ability to Elicit Rich Responses
- Is the question open-ended enough to allow detailed responses?
- Does it avoid yes/no or simple factual answers?
- Does it create space for the interviewee to share insights?

### 4. Natural Conversation Flow
- Does the question feel like a natural continuation of the conversation?
- Does it maintain the conversational tone established?
- Does it respect the interviewee's communication style?

## Judgment Output

The Judge provides:
- **WINNER**: A (first question), B (second question), or TIE
- **REASONING**: 2-3 sentence explanation of the decision

## Interpretation of Results

- **judgment = 0**: Original interviewer question won
- **judgment = 1**: Jane's question won
- **judgment = 2**: Questions tied (equally good)
- **judgment = -1**: Parse failure (unclear judgment)

## Win Rate Interpretation

| Win Rate | Interpretation |
|----------|----------------|
| < 30%    | Jane needs significant improvement |
| 30-45%   | Below baseline, room for improvement |
| 45-55%   | Comparable to human interviewers |
| 55-70%   | Above baseline, good performance |
| > 70%    | Excellent, may indicate bias |

## Notes

- Questions are randomized to prevent position bias
- Each evaluation is independent (no cross-pair learning)
- Judge uses the same evaluation criteria for all pairs
- High tie rates may indicate questions are similarly good or criteria too broad
