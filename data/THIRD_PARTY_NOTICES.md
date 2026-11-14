# Third-party dataset notices

## Mack IT Support Dataset

Source: [benjaminmacklin/IT_Support](https://huggingface.co/datasets/benjaminmacklin/IT_Support), file `B_troubleshooting.jsonl`.
The checked-in sample subset uses 16 selected records and identifies each record by its source-file line. These records are external demonstration material, not approved university procedures.

The dataset card declares the MIT License:

```text
MIT License

Copyright (c) 2025 MBGOC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The checked-in classifier training subset contains 140 issue descriptions from this dataset. Their ticket categories were assigned by IntelliDesk for this project after reviewing each issue description; the original Mack dataset does not supply these category labels. Each record retains its source file and line number.

## TechQA-RAG-Eval

Source: [NVIDIA TechQA-RAG-Eval](https://huggingface.co/datasets/nvidia/TechQA-RAG-Eval). The selected evaluation-only questions and supporting passages are kept in `evaluation/test_questions.json`; they are not loaded into the application knowledge base. The dataset card declares Apache-2.0; see the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

## Excluded source

The [UmerSajid IT Troubleshooting Dataset](https://huggingface.co/datasets/UmerSajid/IT-Troubleshooting-Dataset) was inspected but not copied into this project because its dataset card and README do not declare a license.
