tl;dr
This PR fixes an issue where automatic ETag generation was inadvertently disabled when `res.send()` was used with a `Transfer-Encoding` header.

Your Understanding
Your understanding is largely correct! You've accurately identified the core problem: a previous commit, while correctly preventing `Content-Length` from being set with `Transfer-Encoding`, also unintentionally broke ETag generation. You also correctly identified the fix: the PR separates the logic for calculating body length (needed for ETags) from the conditional setting of the `Content-Length` header.

The most significant gap in your understanding is about the purpose of ETags. While you understand *that* they stopped being generated, you're asking *what* they do in the broader context of a web application.

Changes
The changes in this PR are focused on the `res.send` function in `lib/response.js` and a new test case in `test/res.send.js`.

**`lib/response.js`**

*   **Lines 162-179 (modified):** The core change here is how `len` (the body length) is calculated and how `Content-Length` is set.
    *   Previously, the entire block for calculating `len` and then setting `Content-Length` was wrapped in an `if (chunk !== undefined && !this.get('Transfer-Encoding'))` condition. This meant that if `Transfer-Encoding` was present, `len` would never be calculated, and thus, the ETag could not be generated.
    *   Now, the `len` calculation (lines 164-179) is performed unconditionally if `chunk` is defined. This ensures that the body length is always determined, regardless of the `Transfer-Encoding` header.
    *   The `Content-Length` header, however, is still conditionally set *after* `len` is calculated, specifically only if `!this.get('Transfer-Encoding')` (lines 175-178). This maintains the correct behavior of not sending both `Content-Length` and `Transfer-Encoding` headers simultaneously.

**`test/res.send.js`**

*   **Lines 616-630 (added):** A new test case has been added to specifically verify the fix.
    *   It creates an Express app that sets the `Transfer-Encoding` header to `'chunked'` and then sends a simple string "hello".
    *   It then asserts that:
        *   The `Content-Length` header is *not* present (`shouldNotHaveHeader('Content-Length')`).
        *   The `Transfer-Encoding` header *is* present (`shouldHaveHeader('Transfer-Encoding')`).
        *   An `ETag` header *is* present and matches the expected value (`'ETag', 'W/"5-qvTGHdzF6KLavt4PO0gs2a6pQ00"'`).
        *   The response status is 200 and the body is "hello".
    *   This new test directly confirms that the ETag is generated even when `Transfer-Encoding` is used, validating the PR's fix.

Discussion
The PR description clearly explains the problem: a previous commit (specifically `18e5985b`) correctly prevented `Content-Length` from being set when `Transfer-Encoding` was present, but inadvertently moved the body-length calculation inside the same conditional block. This meant that responses using `Transfer-Encoding` stopped receiving an ETag because ETag generation relies on knowing the body length. The fix involves separating these concerns: always calculate the body length for ETag generation, but only set the `Content-Length` header if `Transfer-Encoding` is not present, thus preserving both functionalities correctly. There are no comments in the thread to summarize.

Learning
1.  How do ETags contribute to client-side caching and reducing server load, and what are the potential implications of an incorrect or missing ETag on a web application's performance and user experience?
2.  The `Transfer-Encoding` header indicates how the payload body is encoded to safely transfer to the user. What are some common values for `Transfer-Encoding` other than `chunked`, and when might you choose to use them?
3.  The PR mentions that `Content-Length` and `Transfer-Encoding` "can't be present in the response headers together." Why is this a rule in HTTP, and what happens if a server were to send both?