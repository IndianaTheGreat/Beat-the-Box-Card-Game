/*
==============================================
NODE BUILT-INS USED BY THE TESTS (TYPES ONLY)
==============================================
File Location: Beat-the-Box-Card-Game/extension/tests/node.d.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-21
Last Tested: 2026-10-21 (tsc 7.0.2 --noEmit: no errors; node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-21):
- New. Describes the few parts of Node the tests import (node:test,
  node:assert/strict, node:fs), so VS Code and the type check know them.
  Before, VS Code underlined those imports in red ("Cannot find name
  'node:test'") because nothing told TypeScript about Node's modules.

DESCRIPTION:
-----------
Types only: there is no code here and nothing runs it. Node itself
provides these modules; this file just tells TypeScript what they look
like. It stands in for the @types/node package, so the extension still
needs no npm install.

DEPENDENCIES:
------------
- None.

KEY FUNCTIONS:
-------------
- node:test -> describe(name, fn), test(name, fn)
- node:assert/strict -> assert.equal, notEqual, deepEqual, ok, throws
- node:fs -> readFileSync(path, "utf8")

NOTES:
-----
- Only what the tests use is described. If a test starts using another
  Node function (assert.match, say), add it here, or the type check will
  say it doesn't exist.
- If the project ever installs @types/node, delete this file.
*/

declare module "node:test" {
  /** A group of tests. */
  export function describe(name: string, fn: () => void): void;
  /** One test. It fails if fn throws (or its promise rejects). */
  export function test(name: string, fn: () => void | Promise<void>): void;
}

declare module "node:assert/strict" {
  /** Something assert.throws can check the error against: a class, a
   * pattern for the message, or a function that returns true. */
  type ErrorCheck = (abstract new (...args: never[]) => Error) | RegExp | ((error: unknown) => boolean);

  interface Assert {
    /** Same value (===, so 1 and "1" differ). */
    equal(actual: unknown, expected: unknown, message?: string): void;
    notEqual(actual: unknown, expected: unknown, message?: string): void;
    /** Same contents, compared all the way down. */
    deepEqual(actual: unknown, expected: unknown, message?: string): void;
    ok(value: unknown, message?: string): asserts value;
    /** fn must throw (an error that passes `check`, when given). */
    throws(fn: () => unknown, check?: ErrorCheck, message?: string): void;
  }

  const assert: Assert;
  export default assert;
}

declare module "node:fs" {
  /** Read a whole text file. */
  export function readFileSync(path: string | URL, encoding: "utf8"): string;
}