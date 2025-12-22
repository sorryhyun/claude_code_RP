/**
 * Whiteboard Diff Parser and Applier
 *
 * Parses diff output from 화이트보드 agent and applies it to maintain full state.
 *
 * Diff Format:
 * - `+ line` : Add line
 * - `- line` : Remove line
 * - `~ old → new` : Modify line
 * - `CLEAR` : Clear entire board
 */

export interface WhiteboardState {
  lines: string[];
  isEmpty: boolean;
}

export type DiffOperation =
  | { type: 'add'; content: string }
  | { type: 'remove'; content: string }
  | { type: 'modify'; oldContent: string; newContent: string }
  | { type: 'clear' };

/**
 * Check if a message contains whiteboard diff
 */
export function isWhiteboardDiff(content: string): boolean {
  return content.includes('[화이트보드 diff]');
}

/**
 * Parse whiteboard diff from message content
 */
export function parseWhiteboardDiff(content: string): DiffOperation[] {
  const operations: DiffOperation[] = [];

  // Strip code block markers if present
  let cleanContent = content.trim();
  if (cleanContent.startsWith('```')) {
    cleanContent = cleanContent.replace(/^```\n?/, '').replace(/\n?```$/, '');
  }

  // Extract content after [화이트보드 diff]
  const diffMatch = cleanContent.match(/\[화이트보드 diff\]\s*([\s\S]*)/);
  if (!diffMatch) return operations;

  const diffContent = diffMatch[1].trim();
  const lines = diffContent.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed === 'CLEAR') {
      operations.push({ type: 'clear' });
      continue;
    }

    if (trimmed.startsWith('+ ')) {
      operations.push({ type: 'add', content: trimmed.slice(2) });
      continue;
    }

    if (trimmed.startsWith('- ')) {
      operations.push({ type: 'remove', content: trimmed.slice(2) });
      continue;
    }

    if (trimmed.startsWith('~ ')) {
      // Format: ~ old content → new content
      const modifyContent = trimmed.slice(2);
      const arrowIndex = modifyContent.indexOf(' → ');
      if (arrowIndex !== -1) {
        operations.push({
          type: 'modify',
          oldContent: modifyContent.slice(0, arrowIndex),
          newContent: modifyContent.slice(arrowIndex + 3),
        });
      }
      continue;
    }
  }

  return operations;
}

/**
 * Apply diff operations to whiteboard state
 */
export function applyDiff(
  state: WhiteboardState,
  operations: DiffOperation[]
): WhiteboardState {
  let lines = [...state.lines];

  for (const op of operations) {
    switch (op.type) {
      case 'clear':
        lines = [];
        break;

      case 'add':
        lines.push(op.content);
        break;

      case 'remove': {
        // Find and remove the line (fuzzy match to handle whitespace differences)
        const normalizedTarget = normalizeForMatch(op.content);
        const index = lines.findIndex(
          (line) => normalizeForMatch(line) === normalizedTarget
        );
        if (index !== -1) {
          lines.splice(index, 1);
        }
        break;
      }

      case 'modify': {
        // Find and replace the line
        const normalizedOld = normalizeForMatch(op.oldContent);
        const index = lines.findIndex(
          (line) => normalizeForMatch(line) === normalizedOld
        );
        if (index !== -1) {
          lines[index] = op.newContent;
        }
        break;
      }
    }
  }

  return {
    lines,
    isEmpty: lines.length === 0,
  };
}

/**
 * Normalize line for fuzzy matching (handles whitespace differences)
 */
function normalizeForMatch(line: string): string {
  return line.replace(/\s+/g, ' ').trim();
}

/**
 * Render whiteboard state as displayable content
 */
export function renderWhiteboard(state: WhiteboardState): string {
  if (state.isEmpty) {
    return '';
  }
  return `[화이트보드]\n${state.lines.join('\n')}`;
}

/**
 * Create initial empty whiteboard state
 */
export function createEmptyWhiteboard(): WhiteboardState {
  return {
    lines: [],
    isEmpty: true,
  };
}

/**
 * Process a message and update whiteboard state if it's a diff
 * Returns the updated state and whether it was modified
 */
export function processWhiteboardMessage(
  content: string,
  currentState: WhiteboardState
): { state: WhiteboardState; wasUpdated: boolean } {
  if (!isWhiteboardDiff(content)) {
    return { state: currentState, wasUpdated: false };
  }

  const operations = parseWhiteboardDiff(content);
  if (operations.length === 0) {
    return { state: currentState, wasUpdated: false };
  }

  const newState = applyDiff(currentState, operations);
  return { state: newState, wasUpdated: true };
}
