# Where the Neural Network Lives in an LLM: Training vs. Generating, Start to Finish

Short answer: **the same neural network is used for both** — training and generating are two different *modes* of running the exact same network. Training is how the network's weights get set; generating is using those already-set weights to produce answers. This guide walks the entire pipeline end to end and marks exactly where the neural network does its work at each stage.

```mermaid
flowchart LR
    A["🧠 One Neural Network<br/>(the Transformer)"] --> B["Mode 1: TRAINING<br/>Weights get ADJUSTED<br/>(learning phase)"]
    A --> C["Mode 2: GENERATING<br/>Weights are FROZEN,<br/>just used to predict<br/>(inference phase)"]
```

---

## 1. The Big Picture: One Pipeline, Two Modes

```mermaid
flowchart TD
    T["📝 Text"] --> TOK["Tokenizer<br/>(NOT a neural network —<br/>a fixed lookup algorithm)"]
    TOK --> IDS["Token IDs"]
    IDS --> EMB["Embedding Layer<br/>(a lookup table — IS part<br/>of the neural network,<br/>and IS trained)"]
    EMB --> NN["🧠 Transformer Neural Network<br/>(dozens of attention + feedforward layers)<br/>THIS is 'the brain' doing the heavy lifting"]
    NN --> OUT["Output: probabilities<br/>over every possible next token"]
    OUT -->|"TRAINING MODE:<br/>compare to correct answer,<br/>backprop, adjust weights"| LEARN["📉 Weights improve"]
    OUT -->|"GENERATING MODE:<br/>pick a token, repeat"| GEN["💬 Text appears,<br/>one token at a time"]
```

Two things are **not** neural network computation, and it's worth being precise about this:
- **The tokenizer** (splitting text into tokens) is a fixed, rule-based algorithm — no learning involved, no weights.
- Everything from the **embedding layer onward** *is* the neural network — including the embedding table itself, which is trained just like every other weight.

---

## 2. Where Exactly Is "The Neural Network"?

```mermaid
flowchart TD
    subgraph OUTSIDE["Outside the Neural Network"]
    TOK["Tokenizer<br/>(fixed rules, no learning)"]
    end
    subgraph INSIDE["Inside the Neural Network (all learned/trained)"]
    EMB["Embedding Layer"]
    A1["Attention Layer 1"]
    F1["Feedforward Layer 1"]
    A2["Attention Layer 2"]
    F2["Feedforward Layer 2"]
    DOTS["... (repeated dozens of times,<br/>up to 100+ layers in frontier models)"]
    AN["Attention Layer N"]
    FN["Feedforward Layer N"]
    UNEMB["Output/Unembedding Layer"]
    end
    TOK --> EMB --> A1 --> F1 --> A2 --> F2 --> DOTS --> AN --> FN --> UNEMB
```

Every box inside "INSIDE" has **weights** — numbers that started random and were tuned during training. That entire stack, repeated dozens or hundreds of times, *is* the neural network. When people say an LLM has "70 billion parameters," they're counting every single weight across every one of these layers.

---

## 3. TRAINING MODE — Where the Network Actually Learns

Training is where the neural network's weights go from random noise to something that captures language, knowledge, and reasoning patterns. This happens **once** (an expensive, months-long process), before the model is ever released to users.

```mermaid
flowchart TD
    A["Take a huge chunk of real text<br/>e.g. 'The cat sat on the mat'"] --> B["Hide the last word:<br/>'The cat sat on the'"]
    B --> C["Tokenize + Embed<br/>(same steps as generating)"]
    C --> D["🧠 Forward pass through<br/>the neural network"]
    D --> E["Network predicts probabilities<br/>for the next token<br/>e.g. 'mat': 15%, 'floor': 10%, 'moon': 0.001%"]
    E --> F["Compare to the ACTUAL next word<br/>('mat') — calculate loss<br/>(how wrong was the guess?)"]
    F --> G["Backpropagation<br/>calculate how much every single<br/>weight contributed to the error"]
    G --> H["Gradient descent<br/>nudge EVERY weight in the network<br/>slightly toward being less wrong"]
    H --> I["Repeat with the NEXT chunk<br/>of text — billions/trillions of times"]
    I --> D
```

**This is the exact same forward-pass → loss → backpropagation → gradient-descent loop from the earlier neural network guide** — just running on a network with billions of neurons, on a dataset with trillions of tokens, on thousands of specialized computer chips (GPUs/TPUs), running for weeks or months.

### What actually changes during training

```mermaid
flowchart LR
    A["Before training:<br/>random weights<br/>Predicts gibberish"] --> B["After some training:<br/>weights capture grammar<br/>Predicts plausible-looking sentences"] --> C["After lots of training:<br/>weights capture facts,<br/>reasoning patterns, style<br/>Predicts genuinely useful text"]
```

### The three training stages (from an earlier guide, now placed correctly)

```mermaid
flowchart LR
    P["1. Pretraining<br/>🧠 network learns from<br/>raw internet-scale text<br/>(next-token prediction)"] --> F["2. Fine-tuning<br/>🧠 SAME network, further trained<br/>on curated Q&A examples"]
    F --> R["3. RLHF<br/>🧠 SAME network, further trained<br/>using human preference rankings"]
    R --> D["Frozen, deployed model<br/>ready for generating"]
```

Notice: it's **one continuous network** across all three stages — pretraining doesn't produce one model that gets thrown away and replaced. The same weights keep getting refined, stage after stage.

---

## 4. GENERATING MODE — Where the (Now-Frozen) Network Gets Used

Once training is complete, the weights are **frozen** — locked in place. Every time you chat with the model, it runs the exact same neural network, using those fixed weights, purely to compute predictions. No learning happens during your conversation (nothing you say updates the model's actual weights).

```mermaid
sequenceDiagram
    participant You
    participant Tokenizer
    participant NN as 🧠 Neural Network<br/>(frozen weights)
    participant Output

    You->>Tokenizer: "The capital of France is"
    Tokenizer->>NN: Token IDs -> Embeddings
    NN->>NN: Forward pass ONLY<br/>(no backprop, no weight updates)
    NN->>Output: Probability distribution<br/>over next token
    Output-->>You: "Paris" (highest probability)
    You->>Tokenizer: "The capital of France is Paris"
    Tokenizer->>NN: Updated token sequence
    NN->>NN: Forward pass again
    NN->>Output: Next probability distribution
    Output-->>You: "."
    Note over You,Output: Repeats one token at a time,<br/>each time re-running the SAME<br/>frozen network on the growing text
```

**Key distinction from training:**

| | Training | Generating (Inference) |
|---|---|---|
| **Weights** | Being adjusted constantly | Completely frozen |
| **Backpropagation** | Happens every step | Never happens |
| **Direction of computation** | Forward AND backward | Forward only |
| **Goal** | Make the network more accurate | Use the (already accurate) network to answer |
| **Cost** | Extremely expensive (months, huge compute) | Much cheaper per response (still real, but far less) |
| **Happens** | Once, before release (occasionally updated with new versions) | Every single time you send a message |

---

## 5. The Full End-to-End Walkthrough: One Sentence, Start to Finish

Let's trace "Explain gravity" through the *entire* system, marking every step:

```mermaid
flowchart TD
    A["📝 You type:<br/>'Explain gravity'"] --> B["✂️ TOKENIZER<br/>(no neural network)<br/>splits into tokens:<br/>['Explain', ' gravity']"]
    B --> C["🔢 Token IDs<br/>(no neural network)<br/>[36145, 24552]"]
    C --> D["🧭 EMBEDDING LAYER<br/>(neural network, trained)<br/>IDs → meaning vectors<br/>[0.2,-0.5,...] [0.8,0.1,...]"]
    D --> E["🧠 TRANSFORMER LAYERS<br/>(neural network, trained)<br/>Attention: which words matter<br/>Feedforward: process the info<br/>Repeated ~dozens of times"]
    E --> F["📊 OUTPUT LAYER<br/>(neural network, trained)<br/>probability over EVERY<br/>possible next token"]
    F --> G["🎲 Sampling<br/>(simple algorithm, not the NN)<br/>picks a token, e.g. 'Gravity'"]
    G --> H["🔁 Loop: feed 'Gravity' back in,<br/>predict the NEXT token,<br/>repeat until the response is done"]
    H --> I["✂️ TOKENIZER converts<br/>final token IDs back to text"]
    I --> J["💬 'Gravity is the force<br/>that attracts objects...'"]
```

**So, to directly answer the question:** the neural network is used for **both** training and generating — but it does fundamentally different *jobs* in each:
- **In training**, the network is the *thing being changed* — every weight inside it gets adjusted to reduce prediction error, over trillions of examples.
- **In generating**, the network is the *thing doing the work* — its already-learned weights are used, unchanged, to compute a probability distribution over what word should come next, repeatedly, to build your response.

---

## 6. Why This Split Matters (Practical Implications)

```mermaid
flowchart TD
    A["Training happens ONCE,<br/>ahead of time"] --> A1["This is why the model has<br/>a 'knowledge cutoff' date —<br/>it only knows what was in its<br/>training data"]
    B["Generating happens EVERY<br/>conversation, using frozen weights"] --> B1["This is why the model has<br/>NO memory between separate<br/>chats by default — nothing<br/>you say changes its weights"]
    C["Both use the SAME<br/>architecture"] --> C1["This is why tools like web search<br/>exist — to feed the frozen network<br/>fresh information at generation time,<br/>since it can't 'learn' it on the fly"]
```

This also explains why an assistant can be given new information mid-conversation (like a document you upload, or a memory summary of past chats) — that information isn't changing the network's weights, it's just extra text added to the input that flows through the same frozen network as additional context, exactly the way your original question does.

---

## Quick Reference

| Stage | Neural network involved? | What happens |
|---|---|---|
| **Tokenization** | ❌ No — fixed algorithm | Text split into tokens, tokens mapped to IDs |
| **Embedding lookup** | ✅ Yes — trained weights | Token IDs converted into meaning-vectors |
| **Transformer layers (attention + feedforward)** | ✅ Yes — trained weights | The "thinking" — context is weighed, patterns processed |
| **Output layer** | ✅ Yes — trained weights | Produces probability distribution over next token |
| **Sampling** | ❌ No — simple algorithm | Picks an actual token from the probability distribution |
| **Training update (backprop)** | ✅ Yes — this IS training | Weights adjusted based on prediction error |

| Mode | Weights | Direction | When it happens |
|---|---|---|---|
| **Training** | Being adjusted | Forward + backward | Once, before release (by the AI company) |
| **Generating** | Frozen | Forward only | Every time you chat with the model |

---

## Explore Further

| Site | What you can do there |
|---|---|
| [transformer-circuits.pub](https://transformer-circuits.pub/) | Anthropic's research publications visually breaking down what's actually happening inside trained Transformer networks |
| [bbycroft.net/llm](https://bbycroft.net/llm) | An incredible interactive 3D visualization of a real LLM's full architecture — watch tokens flow through embeddings, attention, and output layers live |
| [jalammar.github.io/illustrated-transformer](https://jalammar.github.io/illustrated-transformer/) | The most famous visual, step-by-step walkthrough of the Transformer architecture |
| [playground.tensorflow.org](https://playground.tensorflow.org/) | Revisit this to reinforce the training loop (forward pass, loss, gradient descent) on a tiny scale before mapping it onto LLM-scale training |

**Try this:** open bbycroft.net/llm and pick the smallest model shown. Type a sentence and watch it visually animate the exact pipeline from this guide — tokenization, embedding, attention layers lighting up, and the final probability distribution — happening in real time on a real (small) model.
