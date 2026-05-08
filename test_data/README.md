# Test Data

Sample document pairs for testing the semantic diff tool.

## Sample 1: Personal Statement

**Expected behavior:**
- Sentence 1: YELLOW - moderate drift (first person → third person)
- Sentence 2: YELLOW - moderate drift ("doing this with" vs "has friends at")
- Sentence 3: RED - major drift (removes building aspect, assumes winning)

## Sample 2: Business Document

**Expected behavior:**
- Sentence 1: YELLOW - moderate drift ("should consider" → "plan to", commitment level)
- Sentence 2: GREEN - meaning preserved (style change only)
- Sentence 3: ADDED - new sentence in v2, no v1 counterpart

## Usage

Copy and paste the contents of v1 and v2 files into the frontend text areas to test the comparison pipeline.
