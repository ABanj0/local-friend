/** Session-scoped retry budget. Only an explicit manual retry replenishes it. */
export class Recovery {
  attempts = 0;
  nextDelay(): number | null {
    if (this.attempts >= 3) return null;
    return 1000 * 2 ** this.attempts++;
  }
  reset() { this.attempts = 0; }
}
