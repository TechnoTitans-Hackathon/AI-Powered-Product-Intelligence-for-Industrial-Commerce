# How It Works: A Simple Explanation

UniHack is designed to take minimal, messy information about an industrial product (like just a brand name and a part number) and turn it into a complete, verified data sheet ready for an online store.

Here is how the pipeline works step-by-step:

### INPUT
The process starts when a user types in basic product details into the frontend, such as "Schneider Electric" and "ATV630U55N4". The user also selects how deeply they want the system to think (e.g., using a local AI).

### DISCOVER
The first AI agent wakes up and looks at the input. It asks itself: "What do I already know about this product, and what vital specifications am I missing based on what this product is?" It creates a checklist of missing information.

### FIND EVIDENCE
The system then acts like a librarian. It searches through its connected databases and documents to find chunks of text (evidence) that contain the answers to the checklist created in the Discover phase.

### DECIDE
Before proceeding, the system makes a "Knowledge Decision". It looks at the evidence it found and asks: "Do I have enough information to accurately describe this product?" If yes, it moves on. If no, it flags that more research is needed.

### EXTRACT
A second AI agent, the "Intelligence Agent", reads all the gathered evidence. Its strict job is to extract the exact technical specifications (like voltage, wattage, and dimensions) strictly from the text provided, without guessing or hallucinating.

### NORMALIZE
AI models can be messy. The system takes the raw data the AI extracted and "normalizes" it, forcing it into standardized formats (e.g., converting "5.5kW" and "5.5 kilowatts" into a single standard format).

### VALIDATE
This is the most critical step. The system deterministically checks the AI's homework. It looks at every single fact the AI extracted and verifies if that fact actually exists in the original evidence text. If the AI hallucinated a fact, it gets flagged as a conflict.

### SCORE
Based on the validation step, the system assigns a confidence score to every data point. Facts explicitly found in the evidence get a high score, while inferred or missing facts get a low score.

### STRUCTURE
Finally, the system maps all these verified facts into our massive 252-column commerce schema. This ensures the data is perfectly formatted for an industrial database or e-commerce platform, ready to be exported and used.
