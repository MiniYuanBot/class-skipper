# Markdown Formatting Guidelines

## 1. Heading Hierarchy

```markdown
## Chapter Topic

### Core Concept / Method

#### Specific Detail / Derivation
```

- Use at most `####` four-level headings
- Do not use `#` one-level headings (to avoid conflicts with the document's overall title)
- Each heading should be **semantically clear**, making it easy to quickly locate knowledge points

---

## 2. Language and Terminology Guidelines

### 2.1 Language Style

- **Notes must be written primarily in Chinese**, in a natural and fluent style suitable for teaching
- Use colloquial yet professional expressions, such as:
  - "In other words…"
  - "In essence…"
  - "It is worth noting that…"
  - "For example…"
  - "As an analogy…"

### 2.2 Handling English Terminology

- At first occurrence: **Chinese + English in parentheses + optional bold**

  ```markdown
  Chinese translation of Convolution (Convolution)
  Chinese translation of Gradient (Gradient)
  Chinese translation of end-to-end (end-to-end)
  ```

- On subsequent occurrences: you may use Chinese alone, or a mix of Chinese and English, but keep it consistent
- Core terms may be appropriately bolded for emphasis: **Chinese translation of Backpropagation (Backpropagation)**

---

## 3. Content Structure Guidelines

### 3.1 Standard Order of Development for Knowledge Points

For each **core concept / method**, it is recommended to develop it in the following order:

```markdown
### Concept Name (English)

**Definition**: …
**Core Idea**: …
**Background and Purpose**: …
**Mathematical Expression** (if any): …
**Intuitive Understanding**: …
```

### 3.2 How to Break Down Algorithms / Processes

```markdown
The steps of **Algorithm Name** are as follows:

1. **Name of Step 1**
   - Input: …
   - Operation: …
   - Output: …
   - Purpose: …

2. **Name of Step 2**
   - …
```

### 3.3 Use Tables for Comparisons

```markdown
| Method | Advantages | Disadvantages | Applicable Scenarios |
| :--- | :--- | :--- | ---: |
| Method A | Converges fast | Prone to overfitting | Sufficient data |
| Method B | Stable | Slow to compute | Small datasets |
```

**Table guidelines**:

- Keep one space on each side of every `|`
- There is one space after the first `|` of each row and one space before the last `|`
- Alignment markers:
  - `:---` left-aligned
  - `---:` right-aligned
  - `:---:` center-aligned

---

## 4. Formula Guidelines (Mandatory)

### Standard Template

```markdown
Definition of the loss function:
$$
\mathcal{L}(\theta) = -\frac{1}{n} \sum_{i=1}^n \left[ y^{(i)}\log h(x^{(i)}; \theta) + (1-y^{(i)})\log(1-h(x^{(i)}; \theta)) \right]
$$

**Notation explanation**:
- $n$: the total number of samples
- $y^{(i)} \in \{0,1\}$: the true label of the $i$-th sample
- $h(x^{(i)}; \theta) \in [0,1]$: the probability the model predicts class 1
- $\theta$: the model parameters to be optimized

**Meaning explanation**:
This formula measures the discrepancy between the predicted probability distribution and the true distribution; the smaller the value, the more accurate the model's predictions.

**Physical/geometric meaning**:
It is equivalent to minimizing the cross-entropy between two probability distributions, making the model's output as close to the true labels as possible.
```

### How to Embed Formulas

- Display formulas: use `$$ ... $$` and place them on their own line
- Inline formulas: use `$ ... $`
- Multiple aligned formulas: use `\begin{aligned} ... \end{aligned}`

---

## 5. Interactive Elements (Mandatory)

At the end of every major knowledge point or chapter, the following must be included:

```markdown
### Frequently Asked Questions and Answers

**Q1: Why use the logarithmic form rather than directly minimizing the prediction error?**
> Directly minimizing the error (e.g., MSE) causes vanishing gradients in classification problems; the logarithmic form turns multiplication into addition, is more numerically stable, and the penalty for wrong predictions grows exponentially.

**Q2: What is the relationship between the cross-entropy loss and maximum likelihood estimation?**
> The two are mathematically equivalent. Minimizing cross-entropy is equivalent to maximizing the likelihood function; both seek the model parameters that make the observed data most probable.
```

- At least 1–3 Q&A items per chapter
- Questions must be of real value, and answers must be thorough

---

## 6. Annotation and Emphasis Guidelines

### 6.1 Important Notes

```markdown
**Note**: Although learning-based methods often perform better on many vision tasks, classical methods still hold value in data-scarce or real-time/embedded scenarios.
```

### 6.2 Annotating Common Pitfalls

```markdown
**Common pitfalls**:
- Confusing the use cases of softmax and sigmoid
- Forgetting to normalize the input, leading to exploding gradients
```

---

## 7. List Guidelines

### Unordered Lists

```markdown
- First item
  - Sub-item (indented by two spaces)
- Second item
```

### Ordered Lists

```markdown
1. First step
2. Second step
   1. Sub-step (indented by three spaces)
   2. Sub-step
```

---

## 8. Code and Pseudocode

### Pseudocode Example

```markdown
**Training process**:

1. **Forward**: compute the output probabilities and the Loss from the input
2. **Backpropagation**: compute the parameter gradients
3. **Gradient Descent**: update the parameters (SGD / Mini-batch)
4. Repeat until convergence or until the training epochs are reached
```

### Real Code (Optional)

```python
# Short example
for epoch in range(num_epochs):
    for x_batch, y_batch in dataloader:
        pred = model(x_batch)
        loss = loss_fn(pred, y_batch)
        loss.backward()
        optimizer.step()
```

---

## 9. Diagram Descriptions (When No Image Is Available)

If there is no image, a clear text description can be used instead:

```markdown
**Structural sketch**:

Input layer (784 dims) → Hidden layer (256 dims, ReLU) → Hidden layer (128 dims, ReLU) → Output layer (1 dim, Sigmoid)
```

---

## 10. Overall Document Structure Template

```markdown
# Course Name - Chapter Name

## Major Section 1

### Concept 1
Content + formulas + examples + Q&A

### Concept 2
Content + table comparison + Q&A

---

## Major Section 2

### Method 1
Algorithm steps + derivation + precautions + Q&A

### Method 2
```

---

## Quality Checklist

- [ ] Every core concept includes: definition / idea / background / analogy
- [ ] Every formula includes: LaTeX / notation explanation / meaning explanation / physical meaning
- [ ] Every abstract knowledge point is accompanied by a concrete example
- [ ] Each chapter ends with 1–3 Q&A items
- [ ] English terms are all annotated in parentheses, and core terms may be bolded
- [ ] Tables follow the compact style (spaces around `|`, correct alignment markers)
- [ ] At least one comparison table (with ≥ 3 comparison dimensions)
- [ ] No formula or term appears alone without an explanation

English-documentation normalization: the four Chinese terminology examples above were translated into explanatory English. The original rules and their limitations are otherwise retained; standards/MARKDOWN.md is the active revised standard.
