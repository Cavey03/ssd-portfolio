"""Content for the ITRI626 study summaries.

Source: Andrew W. Trask, *Grokking Deep Learning* (Manning, 2019). Citations give the book's printed chapter
and page. Anything not in the book is wrapped in X(...) and shows a "Not in Trask" marker.
Write in my own words; never paste long passages from the book.
"""
import html
import re

from figs import (activations, bowls, conv, flow, kmeans, nested, net, neuron, overfit, pool, splitbar, svm,
                  transfer)


# ---------- small markup helpers ----------
def C(ch, p):
    return f'<span class="cite" title="Trask, Grokking Deep Learning, chapter {ch}, page {p}">Ch {ch} · p {p}</span>'


def P(*parts):
    return "<p>" + " ".join(parts) + "</p>"


def H(s):
    return f"<h3>{s}</h3>"


def UL(*items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def OL(*items):
    return "<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"


def EQ(*lines):
    return '<div class="eq">' + "<br>".join(lines) + "</div>"


def CODE(src, note=""):
    esc = html.escape(src.strip("\n"))
    esc = re.sub(r"(#[^\n]*)", r'<span class="c">\1</span>', esc)
    n = f'<div class="code-note">{note}</div>' if note else ""
    return f"<pre><code>{esc}</code></pre>{n}"


def X(*parts, tag="Not in Trask"):
    return f'<div class="xtra"><span class="xtag">{tag}</span>{"".join(parts)}</div>'


def FIG(svg, cap):
    return f'<figure class="fig">{svg}<figcaption>{cap}</figcaption></figure>'


def TBL(head, rows):
    """rows: lists of cells; a row whose first item is 'x' is marked as not in Trask."""
    th = "".join(f"<th>{h}</th>" for h in head)
    body = []
    for r in rows:
        cls = ""
        if r and r[0] == "x":
            cls, r = ' class="xrow"', r[1:]
        body.append(f"<tr{cls}>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def MINE(text, href):
    return (f'<a class="mine" href="{{root}}{href}"><span class="mine-k">In my portfolio</span>'
            f'<span class="mine-t">{text}</span><span class="mine-a" aria-hidden="true">→</span></a>')


def T(term, definition, extra=False):
    return {"term": term, "def": definition, "extra": extra}


# =====================================================================================
UNITS = [
    # ---------------------------------------------------------------------------------
    {
        "id": "su1", "code": "SU1", "folder": "su1-machine-learning", "h": 268, "c": 0.14,
        "title": "Machine learning", "kicker": "Study unit 1",
        "chapters": "Trask chapters 2 and 4, with pieces of 3 and 8",
        "lede": "What it means for a machine to learn, the main ways of learning, how parametric and "
                "nonparametric models differ, and how to design and judge a learning algorithm.",
        "outcomes": [
            {
                "id": "learning", "num": "1.1", "sym": "Ln", "src": "mixed",
                "title": "Describe the concept of learning and learning approaches",
                "short": "What learning is",
                "tldr": "A machine learns when it gets better at a task from data instead of being given the rules. "
                        "Every method in Trask follows one loop: predict, compare, learn.",
                "cites": ["Ch 2 · p 10–18", "Ch 3 · p 25", "Ch 4 · p 48–49"],
                "body": [
                    H("Learning, in one sentence"),
                    P("Machine learning is the part of computer science where machines learn tasks they were "
                      "never explicitly programmed to do (Trask quotes Arthur Samuel's definition).", C(2, 11)),
                    P("Trask's shorthand is <b>monkey see, monkey do</b>: the machine watches a pattern and copies it, "
                      "either <b>directly</b> (supervised learning) or <b>indirectly</b> (unsupervised learning).",
                      C(2, 11)),
                    FIG(nested(), "Deep learning is the part of machine learning that mostly uses neural networks. "
                                  "Not all of it is about building general AI. " + C(2, 10)),
                    H("The learning loop"),
                    flow([("Predict", "push the input through the model"),
                          ("Compare", "measure how far off it was (the error)"),
                          ("Learn", "turn each knob to shrink the error")], "repeat for every example, many times"),
                    P("This three-step loop is the core of supervised parametric learning, and of every network in "
                      "the book.", C(2, 16), C(4, "48–49"),
                      "Learning is trial and error: if the prediction was too high, the weight goes down; too low, it "
                      "goes up.", C(3, 25)),
                    H("Learning approaches"),
                    TBL(["Approach", "Learns from", "Example", "Book"], [
                        ["<b>Supervised</b>", "inputs <i>and</i> the correct outputs", "pixels → cat or no cat", C(2, 12)],
                        ["<b>Unsupervised</b>", "inputs only; finds groups", "words → 'cute' or 'delicious' groups",
                         C(2, 13)],
                        ["<b>Parametric</b>", "a fixed set of knobs, trial and error", "neural networks", C(2, "14–15")],
                        ["<b>Nonparametric</b>", "counting; parameters grow with the data", "counting streetlight outcomes",
                         C(2, 18)],
                        ["x", "<b>Semi-supervised</b>", "a few labels plus lots of unlabelled data",
                         "label 1% of images, learn from all", "SU5–7"],
                        ["x", "<b>Reinforcement</b>", "rewards and penalties after acting", "game-playing AI, robots",
                         "—"],
                    ]),
                    P("Trask splits every algorithm two ways at once: supervised <i>or</i> unsupervised, and parametric "
                      "<i>or</i> nonparametric, giving four kinds.", C(2, 14)),
                    X(P("<b>Reinforcement learning</b> has no dataset of right answers. An agent takes actions in an "
                        "environment and gets a reward or penalty afterwards; it learns which actions lead to the most "
                        "reward over time. It's used for game playing, robot control, and the RLHF step that tunes chat "
                        "models.")),
                ],
                "terms": [T("Machine learning", "Machines learning a task from data instead of explicit rules."),
                          T("Predict · compare · learn", "Make a guess, measure the error, adjust the weights."),
                          T("Trial and error", "How parametric models learn: try, check, nudge the knobs."),
                          T("Reinforcement learning", "Learning from rewards after acting, not from labelled answers.",
                            True)],
            },
            {
                "id": "parametric", "num": "1.2", "sym": "Pm", "src": "book",
                "title": "Describe the difference between parametric and non-parametric learning",
                "short": "Parametric vs nonparametric",
                "tldr": "Parametric models have a fixed number of parameters and learn by trial and error. "
                        "Nonparametric models let the data decide how many parameters there are, often by counting.",
                "cites": ["Ch 2 · p 14–19"],
                "body": [
                    H("The definition"),
                    P("A <b>parametric</b> model has a fixed number of parameters. A <b>nonparametric</b> model's number "
                      "of parameters is set by the data, so in principle it can keep growing.", C(2, 14)),
                    P("Trask's analogy: fitting a square peg into the right hole. A baby jams it into every hole until it "
                      "fits (trial and error: parametric). A teenager counts the four sides and looks for the four-sided "
                      "hole (counting: nonparametric).", C(2, 14)),
                    H("Parametric: a machine with knobs"),
                    P("Data goes in, is processed according to the angle of each knob, and a prediction comes out. "
                      "Learning means turning the knobs. <b>Everything the model knows is stored in the knob "
                      "positions.</b>", C(2, 15)),
                    P("Example: predicting a team's chance of winning. If the win/loss record turns out to predict well, "
                      "its knob is turned up; if the number of toes doesn't, that knob is turned down. Each knob is the "
                      "prediction's sensitivity to one input.", C(2, "15–16")),
                    H("Nonparametric: counting"),
                    P("A model watching a foreign streetlight counts how often each light is followed by cars going. "
                      "Three lights give three counts, so three parameters. With five lights it would have five: the "
                      "data decided.", C(2, 18)),
                    TBL(["", "Parametric", "Nonparametric"], [
                        ["Number of parameters", "fixed, chosen by the designer", "grows with the data"],
                        ["How it learns", "trial and error: search for good knob settings", "counting and probabilities"],
                        ["What it stores", "weights (knob positions)", "counts, or the training data itself"],
                        ["In the book", "all of deep learning", "the streetlight counter (only briefly)"],
                    ]),
                    P("The line is blurry: parametric models still size their inputs and outputs to the data (one input "
                      "per pixel). And 'parameter' just means any number used to model the pattern: weights, counts, "
                      "correlation coefficients. Deep learning is parametric.", C(2, 18)),
                    X(P("Common examples outside the book. <b>Parametric</b>: linear regression, logistic regression, "
                        "neural networks. <b>Nonparametric</b>: k-nearest neighbours (keeps every training point and "
                        "compares new points with them), decision trees (grow more splits as data grows), kernel SVMs "
                        "(the number of support vectors depends on the data).")),
                ],
                "terms": [T("Parameter", "Any number the model uses to capture the pattern: weights, counts …"),
                          T("Knob", "Trask's picture of a weight: turning it changes the prediction's sensitivity."),
                          T("k-nearest neighbours", "Nonparametric classic: predict from the closest stored examples.",
                            True)],
            },
            {
                "id": "paradigms", "num": "1.3", "sym": "Pd", "src": "mixed",
                "title": "Describe the difference between machine learning paradigms in relation to how they treat data "
                         "and their application spaces",
                "short": "ML paradigms",
                "tldr": "Paradigms differ in what data they need: supervised needs inputs with correct outputs, "
                        "unsupervised only inputs, semi-supervised a bit of both, and reinforcement learns from rewards.",
                "cites": ["Ch 2 · p 11–13, 17", "Ch 11 · p 201"],
                "body": [
                    H("Supervised: turn one dataset into another"),
                    P("Supervised learning learns to transform an input dataset (what you know) into an output dataset "
                      "(what you want to know). It needs both, for every training example.", C(2, 12)),
                    P("Trask's examples: image pixels → is there a cat; movies you liked → movies you may like; "
                      "someone's words → happy or sad; weather sensors → chance of rain; raw audio → a transcript.",
                      C(2, 11)),
                    P("He calls it the bread and butter of applied AI: most real ML work ends in some kind of "
                      "supervised classifier.", C(2, 12)),
                    H("Unsupervised: group the data"),
                    P("Also transforms one dataset into another, but there's no right answer to copy. You tell it 'find "
                      "patterns and tell me about them'. Clustering is the classic example: datapoints in, cluster "
                      "numbers out. Trask suggests thinking of <i>every</i> kind of unsupervised learning as a form of "
                      "clustering.", C(2, 13)),
                    flow([("puppies · kittens", "→ group 1"), ("pizza · hot dog · burger", "→ group 2"),
                          ("You name them", "1 = cute, 2 = delicious")]),
                    P("An unsupervised parametric model has knobs per group, and outputs the probability (0 to 1) that a "
                      "datapoint belongs to each group.", C(2, 17)),
                    X(H("Other paradigms"),
                      UL("<b>Semi-supervised</b>: a small labelled set plus a large unlabelled one (see SU5–7).",
                         "<b>Reinforcement</b>: no answers, only rewards from an environment after acting.",
                         "<b>Self-supervised</b>: the labels are made from the data itself, such as hiding a word and "
                         "predicting it. This is how LLMs are pretrained. Trask's fill-in-the-blank network is an early "
                         "example " + C(11, 201) + "."),
                      TBL(["Paradigm", "Data it needs", "Application spaces"], [
                          ["Supervised", "labelled pairs (input, answer)",
                           "spam filters, image classification, price prediction, medical diagnosis, speech-to-text"],
                          ["Unsupervised", "inputs only", "customer segments, fraud and anomaly detection, topic discovery"],
                          ["Semi-supervised", "few labels, many unlabelled", "medical images, web-scale text and images"],
                          ["Reinforcement", "rewards from an environment", "games, robotics, recommendations, RLHF"],
                          ["Self-supervised", "raw data; labels made from it", "LLM pretraining, image pretraining"],
                      ]), tag="Not in Trask · rows 1–2 summarise Ch 2"),
                ],
                "terms": [T("Supervised", "Learn inputs → known outputs. Needs labels."),
                          T("Unsupervised", "Find structure (groups) in inputs alone."),
                          T("Clustering", "Turn datapoints into group numbers; you interpret the groups."),
                          T("Self-supervised", "Make labels from the data itself; how LLMs pretrain.", True)],
            },
            {
                "id": "design", "num": "1.4", "sym": "Ds", "src": "mixed",
                "title": "Design and analyse machine learning algorithms",
                "short": "Design and analysis",
                "tldr": "Design means choosing how to predict, how to measure error and how to learn. Analysis means "
                        "checking that it learns, how fast, whether it diverges and whether it works on new data.",
                "cites": ["Ch 3 · p 22", "Ch 4 · p 49–76", "Ch 8 · p 148–152"],
                "body": [
                    H("Designing: three decisions"),
                    OL("<b>Predict</b>: what goes in, what comes out, and how inputs are combined (the network shape). "
                       "Rule of thumb: give the network about as much information as a human would need for the same "
                       "prediction. " + C(3, 22),
                       "<b>Compare</b>: how to measure error. Mean squared error makes every error positive and makes "
                       "big misses count much more than small ones. " + C(4, "50–51"),
                       "<b>Learn</b>: how each weight is updated to reduce the error. Trask calls this error attribution, "
                       "'the blame game'; gradient descent is the standard answer. " + C(4, 49)),
                    H("Analysing: does it actually work?"),
                    P("Trask analyses his first learning rule, <i>hot and cold</i> learning, and finds two problems: "
                      "it's inefficient (several predictions per update), and with a fixed step size it can't land "
                      "exactly on the goal, so it ends up bouncing around it.", C(4, 55)),
                    P("Gradient descent fixes both by computing direction <i>and</i> amount from the error. Analysing it "
                      "further shows it can <b>diverge</b>: with a large input every update overshoots and the error "
                      "explodes. The fix is a learning rate, alpha.", C(4, "72–76")),
                    P("Finally, test it on data it has never seen. A network can get all 1,000 training images right and "
                      "still do much worse on new ones: it memorised instead of generalising.", C(8, "148–150")),
                    TBL(["Question", "How to check", "Book"], [
                        ["Is the error going down?", "print the error every iteration", C(4, "60–62")],
                        ["Is it diverging?", "error growing, predictions flipping sign", C(4, 74)],
                        ["Too slow?", "raise alpha a little; too jumpy, lower it", C(4, 75)],
                        ["Does it generalise?", "compare training vs test accuracy", C(8, "149–150")],
                        ["When to stop?", "watch accuracy on a validation set", C(8, 152)],
                    ]),
                    X(P("More analysis tools: compare with a <b>baseline</b> (e.g. always predicting the most common "
                        "class); choose metrics that suit the problem (accuracy, precision and recall for classes; MSE or "
                        "MAE for numbers); use <b>k-fold cross-validation</b> for a more reliable score on small data; "
                        "and consider cost: training time, memory, and how it scales with more data.")),
                ],
                "terms": [T("Error function", "A number saying how wrong the prediction was, e.g. squared error."),
                          T("Alpha", "Learning rate: a fraction that shrinks each weight update."),
                          T("Divergence", "Updates overshoot more each time and the error explodes."),
                          T("Generalisation", "Doing well on data the model wasn't trained on.")],
            },
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "id": "su2", "code": "SU2", "folder": "su2-neural-networks", "h": 300, "c": 0.15,
        "title": "Neural networks: introduction", "kicker": "Study unit 2",
        "chapters": "Trask chapter 3, with pieces of 6 and 9",
        "lede": "The maths of a single neuron, and the four basic network shapes: one or many inputs, one or many "
                "outputs. My eFundi assignment builds each of them.",
        "outcomes": [
            {
                "id": "neuron", "num": "2.1", "sym": "Nu", "src": "mixed",
                "title": "Understand the basic mathematical model underlying the operation of a single neuron",
                "short": "A single neuron",
                "tldr": "A neuron multiplies each input by a weight, adds them up (a weighted sum), and usually passes "
                        "the result through an activation function.",
                "cites": ["Ch 3 · p 25–30", "Ch 6 · p 121–123", "Ch 9 · p 162"],
                "body": [
                    FIG(neuron(), "Inputs × weights → weighted sum → activation → output"),
                    P("In Trask's simplest network, a neural network is just one or more weights that you multiply by "
                      "the input to make a prediction.", C(3, 25)),
                    P("The input is <b>information</b> and the weight is <b>knowledge</b>: the network uses the "
                      "knowledge in its weights to interpret the information in the input. Every network in the book "
                      "works this way.", C(3, 26)),
                    EQ("one input:&nbsp;&nbsp; prediction = input × weight",
                       "many inputs: prediction = Σ input<sub>i</sub> × weight<sub>i</sub> = input · weights"),
                    P("A weight above 1 amplifies the input, below 1 shrinks it, a negative weight flips it. Trask calls "
                      "each weight a volume knob. Adding up the scaled inputs is the <b>weighted sum</b>, also called "
                      "the <b>dot product</b>.", C(3, "26, 30")),
                    P("From chapter 6 on, the weighted sum goes through an <b>activation function</b> such as relu "
                      "(negative values become 0). Without one, stacking neurons adds no power.", C(6, "121–123"),
                      C(9, 162)),
                    CODE("""
def neuron(inputs, weights):
    total = 0
    for x, w in zip(inputs, weights):
        total += x * w          # weighted sum
    return max(0, total)        # relu activation

print(neuron([8.5, 0.65, 1.2], [0.1, 0.2, 0.0]))   # 0.98
"""),
                    X(EQ("y = f(w · x + b)"),
                      P("Most textbooks add a <b>bias</b> b to the weighted sum, so the neuron can shift its output even "
                        "when every input is 0. Think of it as a weight on an extra input that is always 1. Trask mostly "
                        "leaves it out to keep the code small.")),
                ],
                "terms": [T("Weight", "The knowledge: how much an input counts, and in which direction."),
                          T("Weighted sum", "Multiply each input by its weight and add up. Same as a dot product."),
                          T("Activation function", "Applied to the sum; adds the bend (non-linearity)."),
                          T("Bias", "An extra number added to the sum; shifts the output.", True)],
            },
            {
                "id": "siso", "num": "2.2", "sym": "Si", "src": "book",
                "title": "Describe a single-input, single-output network",
                "short": "Single input, single output",
                "tldr": "One input, one weight, one prediction: prediction = input × weight.",
                "cites": ["Ch 3 · p 24–27"],
                "body": [
                    FIG(net([1, 1], ["# toes"], ["win?"]), "One input node, one weight, one output node"),
                    P("Trask's first network predicts whether a baseball team will win from the average number of toes "
                      "per player. With a weight of 0.1 and an input of 8.5, it predicts 0.85.", C(3, 25)),
                    CODE("""
weight = 0.1

def neural_network(input, weight):
    prediction = input * weight
    return prediction

number_of_toes = [8.5, 9.5, 10, 9]
print(neural_network(number_of_toes[0], weight))   # 0.85
"""),
                    P("Notice: the network knows only what you give it. It doesn't remember the previous game's input.",
                      C(3, 26)),
                    P("A single weight can only <b>scale</b> the input: weight 2 doubles it, 0.01 divides it by 100. So "
                      "this network can only model 'more input → proportionally more (or less) output'.", C(3, 26)),
                    MINE("1-SISO: win probability from creep score (League of Legends)",
                         "su2-neural-networks/1-SISO.ipynb"),
                ],
                "terms": [T("Input", "A number recorded in the real world, easy to know (temperature, toes)."),
                          T("Prediction", "What the network says, given the input. Not always right."),
                          T("Scaling", "What one weight does: multiplies the input up or down.")],
            },
            {
                "id": "miso", "num": "2.3", "sym": "Mi", "src": "book",
                "title": "Describe a multiple-input, single-output network",
                "short": "Multiple inputs, single output",
                "tldr": "Several inputs, one output: multiply each input by its own weight and add them up.",
                "cites": ["Ch 3 · p 28–35"],
                "body": [
                    FIG(net([3, 1], ["# toes", "win/loss", "# fans"], ["win?"]),
                        "Three inputs, three weights, one weighted sum"),
                    P("The number of toes alone isn't a great predictor. Feeding the network the win/loss record and fan "
                      "count too lets it combine information for a better-informed prediction.", C(3, 28)),
                    P("Each input passes through its own volume knob, and the local predictions are added together: a "
                      "<b>weighted sum</b>, or <b>dot product</b>.", C(3, 30)),
                    EQ("pred = 8.5×0.1 + 0.65×0.2 + 1.2×0.0 = 0.85 + 0.13 + 0 = 0.98"),
                    CODE("""
def w_sum(a, b):
    assert len(a) == len(b)
    output = 0
    for i in range(len(a)):
        output += a[i] * b[i]
    return output

weights = [0.1, 0.2, 0]            # toes, win/loss, fans
input = [8.5, 0.65, 1.2]           # first game of the season
print(w_sum(input, weights))       # 0.98
"""),
                    P("The weights show what the network thinks matters. A weight of 0 (fans) means 'ignore this input'; "
                      "a large positive weight means a strong positive link.", C(3, "30–34")),
                    P("NumPy does the same in one call: <code>input.dot(weights)</code>.", C(3, 35)),
                    MINE("2-MISO: win probability from several early-game stats", "su2-neural-networks/2-MISO.ipynb"),
                ],
                "terms": [T("Dot product", "Pairwise multiply two vectors and add: the weighted sum."),
                          T("Vector", "A list of numbers: the inputs, or the weights."),
                          T("Weight of 0", "That input is ignored.")],
            },
            {
                "id": "simo", "num": "2.4", "sym": "Sm", "src": "book",
                "title": "Describe a single-input, multiple-output network",
                "short": "Single input, multiple outputs",
                "tldr": "One input, several outputs: the same input is multiplied by a different weight for each output.",
                "cites": ["Ch 3 · p 36–37"],
                "body": [
                    FIG(net([1, 3], ["win/loss"], ["hurt?", "win?", "sad?"]), "One input fans out to three outputs"),
                    P("Using only the win/loss record, the network predicts three things: the share of players who are "
                      "hurt, whether the team wins, and whether the players are sad.", C(3, 36)),
                    P("The three predictions are <b>completely separate</b>. It behaves like three independent "
                      "single-weight networks that happen to share the same input.", C(3, 36)),
                    EQ("[hurt, win, sad] = 0.65 × [0.3, 0.2, 0.9] = [0.195, 0.13, 0.585]"),
                    CODE("""
def ele_mul(number, vector):
    output = [0, 0, 0]
    for i in range(len(vector)):
        output[i] = number * vector[i]     # same input, different weight
    return output

weights = [0.3, 0.2, 0.9]                  # hurt?, win?, sad?
print(ele_mul(0.65, weights))
"""),
                    MINE("3-SIMO: gold difference at 10 min → win chance, kill lead, objective control",
                         "su2-neural-networks/3-SIMO.ipynb"),
                ],
                "terms": [T("Elementwise multiplication", "Multiply a number (or vector) by each element in turn."),
                          T("Independent outputs", "Each output has its own weight and doesn't affect the others.")],
            },
            {
                "id": "mimo", "num": "2.5", "sym": "Mm", "src": "book",
                "title": "Describe a multiple-input, multiple-output network",
                "short": "Multiple inputs, multiple outputs",
                "tldr": "Several inputs, several outputs: each output does its own weighted sum of all the inputs. "
                        "The weights form a matrix.",
                "cites": ["Ch 3 · p 38–46"],
                "body": [
                    FIG(net([3, 3], ["# toes", "win/loss", "# fans"], ["hurt?", "win?", "sad?"]),
                        "Every input connects to every output"),
                    P("Every input node is connected to every output node. Trask recommends thinking of it as three "
                      "<b>independent weighted sums</b>, one per output.", C(3, 40)),
                    EQ("hurt = 8.5×0.1 + 0.65×0.1 + 1.2×(−0.3) = 0.555",
                       "win&nbsp; = 8.5×0.1 + 0.65×0.2 + 1.2×0.0&nbsp;&nbsp;&nbsp; = 0.98",
                       "sad&nbsp; = 8.5×0.0 + 0.65×1.3 + 1.2×0.1&nbsp;&nbsp;&nbsp; = 0.965"),
                    P("A list of weight vectors is a <b>matrix</b>, and doing a weighted sum with every row is "
                      "<b>vector-matrix multiplication</b>.", C(3, 41)),
                    CODE("""
import numpy as np
weights = np.array([[0.1, 0.1, -0.3],     # hurt?
                    [0.1, 0.2,  0.0],     # win?
                    [0.0, 1.3,  0.1]])    # sad?
input = np.array([8.5, 0.65, 1.2])
print(weights.dot(input))                 # [0.555 0.98 0.965]
"""),
                    H("Stacking: predicting on predictions"),
                    FIG(net([3, 3, 3], names=["inputs", "hidden", "outputs"]), "Two MIMO layers in a row"),
                    P("The outputs of one network can be the inputs of another. The values in the middle form a "
                      "<b>hidden layer</b>. This is the first step towards deep networks.", C(3, 42)),
                    P("Shapes must line up: a (a, b) matrix dotted with a (b, c) matrix gives (a, c); <code>.T</code> "
                      "flips rows and columns.", C(3, 46)),
                    P("Everything in the chapter is <b>forward propagation</b>: activations flow forward from input to "
                      "prediction.", C(3, 46)),
                    MINE("4-MIMO: several stats → several outcomes", "su2-neural-networks/4-MIMO.ipynb"),
                ],
                "terms": [T("Matrix", "A list of vectors: one row of weights per output."),
                          T("Vector-matrix multiplication", "One weighted sum per row of the matrix."),
                          T("Hidden layer", "Predictions used as inputs to the next layer."),
                          T("Forward propagation", "Pushing input through the network to get a prediction.")],
            },
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "id": "su3", "code": "SU3", "folder": "su3-learning-models", "h": 52, "c": 0.15,
        "title": "Learning models: basic applications", "kicker": "Study unit 3",
        "chapters": "Trask chapters 4, 5, 6, 8 and 9, plus Scikit-Learn",
        "lede": "How models learn (gradient descent), why data is split three ways, what activation functions do, "
                "regression and classification both with Scikit-Learn and with neural networks, and the full structure "
                "of a basic deep network.",
        "outcomes": [
            {
                "id": "blackbox", "num": "3.1", "sym": "Bx", "src": "mixed",
                "title": "Describe the black box model of machine learning algorithms",
                "short": "The black box model",
                "tldr": "From outside, a model is a box: data goes in, a prediction comes out, and learning turns knobs "
                        "inside. You judge it by its inputs and outputs, not by reading its insides.",
                "cites": ["Ch 2 · p 15–16", "Ch 3 · p 22, 26", "Ch 6 · p 110"],
                "body": [
                    flow([("Data", "game stats"), ("Machine", "knobs (weights) inside"), ("Prediction", "98% win")],
                         "compare with the truth, turn the knobs, repeat"),
                    P("Trask draws every model the same way: data goes into a 'machine', which turns it into a "
                      "prediction. Inside are knobs; learning means turning them.", C(2, "15–16"), C(3, 22)),
                    P("The interface never changes: input = information, weights = knowledge, output = prediction.",
                      C(3, 26)),
                    P("Trask then looks inside the box: after training on the streetlight data, the weights show which "
                      "input correlates with the output (the middle light's weight is near 1, the others near 0).",
                      C(6, 110)),
                    X(P("<b>Black box</b> is the standard name for this view: you see the inputs and outputs but not "
                        "(easily) the reasoning in between. Simple models like linear regression are fairly transparent, "
                        "since each coefficient means something. Deep networks with millions of weights are close to "
                        "true black boxes, which is why <b>explainable AI</b> tools exist: feature importance, and "
                        "saliency maps that highlight which pixels drove an image prediction. In practice you treat the "
                        "model as a black box and judge it on held-out test data.")),
                ],
                "terms": [T("Model", "The machine: a function with adjustable parameters."),
                          T("Black box", "Judged by inputs and outputs; internals hard to read.", True),
                          T("Explainability", "Tools that show why a model made a prediction.", True)],
            },
            {
                "id": "splits", "num": "3.2", "sym": "Tv", "src": "mixed",
                "title": "Discuss the training, validation and testing functions of data",
                "short": "Training, validation, test",
                "tldr": "Train on one part of the data, tune and decide when to stop on a second part (validation), and "
                        "report the final score on a third part that never influenced the model (test).",
                "cites": ["Ch 8 · p 148–152"],
                "body": [
                    splitbar(),
                    P("Trask trains a network on 1,000 MNIST images until it gets all 1,000 right, then asks the real "
                      "question: how well does it do on images it hasn't seen? He runs it on a separate <b>test "
                      "set</b>.", C(8, 148)),
                    P("Neural networks are only useful on data you don't already know the answer to. Memorising the "
                      "training set is easy; <b>generalising</b> is the goal.", C(8, 149)),
                    FIG(overfit(), "Schematic of Trask's MNIST run: test accuracy peaks early, then falls as the network "
                                   "keeps memorising. " + C(8, 150)),
                    P("To decide when to stop (early stopping), use a <b>validation set</b>, not the test set. If you use "
                      "the test set to control training, you can overfit to the test set as well.", C(8, 152)),
                    TBL(["Split", "Used for", "Book"], [
                        ["<b>Training</b>", "fitting the weights", C(8, 148)],
                        ["<b>Validation</b>", "choosing settings (alpha, size, when to stop)", C(8, 152)],
                        ["<b>Test</b>", "the final, honest score, used once at the end", C(8, "148–149")],
                    ]),
                    X(P("Practical details: typical splits are 70/15/15 or 80/10/10; shuffle before splitting; keep "
                        "class proportions equal in each split (stratify); and avoid <b>data leakage</b>: nothing from "
                        "the test set (not even its mean, for normalising) may be used in training. With little data, "
                        "<b>k-fold cross-validation</b> rotates which part is held out and averages the scores."),
                      CODE("""
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)
X_val, X_test, y_val, y_test = train_test_split(X_test, y_test, test_size=0.5, stratify=y_test, random_state=0)
""")),
                ],
                "terms": [T("Generalisation", "Doing well on new data, not just the training data."),
                          T("Overfitting", "Learning the noise in the training data; test score drops."),
                          T("Early stopping", "Stop training when validation accuracy stops improving."),
                          T("Data leakage", "Test information sneaking into training; inflates the score.", True)],
            },
            {
                "id": "gd", "num": "3.3", "sym": "Gd", "src": "book",
                "title": "Discuss the gradient descent algorithm for training models",
                "short": "Gradient descent",
                "tldr": "Measure the error, use the derivative to find which way and how far each weight should move, "
                        "take a small step (alpha), repeat.",
                "cites": ["Ch 4 · p 47–77", "Ch 5 · p 80–98", "Ch 6 · p 109", "Ch 8 · p 158"],
                "body": [
                    H("The idea"),
                    P("Plot the error against one weight and you get a U-shaped curve. The <b>slope</b> (derivative) at "
                      "the current weight gives the direction (its sign) and the amount (its steepness). Step downhill "
                      "until you reach the bottom, where the error is lowest.", C(4, "68–70")),
                    FIG(bowls(), "Left: each step moves the weight closer to the bottom. Right: with a big input the "
                                 "steps overshoot further each time. " + C(4, "70–74")),
                    H("The update rule"),
                    EQ("delta&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = pred − goal_pred &nbsp;&nbsp;(pure error: direction and amount you missed)",
                       "weight_delta = delta × input &nbsp;&nbsp;(the derivative for this weight)",
                       "weight&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = weight − alpha × weight_delta"),
                    P("Multiplying by the input does three jobs Trask calls <b>scaling</b> (big input → big update), "
                      "<b>negative reversal</b> (a negative input flips the direction) and <b>stopping</b> (input 0 → no "
                      "update, since that weight didn't cause the error).", C(4, "56–57")),
                    CODE("""
weight, goal_pred, input, alpha = 0.5, 0.8, 2, 0.1
for iteration in range(20):
    pred = input * weight                      # predict
    error = (pred - goal_pred) ** 2            # compare
    derivative = input * (pred - goal_pred)    # direction and amount
    weight = weight - alpha * derivative       # learn
    print("Error:", error, "Prediction:", pred)
""", "From Ch 4 p 76. Remove alpha (set it to 1) to watch it diverge."),
                    H("Breaking it: divergence and alpha"),
                    P("With input = 2 and no alpha, every update overshoots and the error explodes: <b>divergence</b>. "
                      "Alpha, a number between 0 and 1, shrinks each update. Choosing it is mostly trial: if the error "
                      "goes up, lower alpha; if learning is too slow, raise it.", C(4, "72–76")),
                    H("Many weights, whole datasets"),
                    P("The same rule works with many weights: each weight's update is the shared delta times its own "
                      "input.", C(5, "80–82"),
                      "Freezing one weight shows that the others still find the bottom: error is shared between all "
                      "the weights.", C(5, 88)),
                    TBL(["Variant", "Updates the weights", "Book"], [
                        ["<b>Stochastic</b>", "after every single example", C(6, 109)],
                        ["<b>Full (batch)</b>", "once per pass, using the average over the whole dataset", C(6, 109)],
                        ["<b>Mini-batch</b>", "after every n examples (e.g. 100): faster, smoother", C(8, 158)],
                    ]),
                    P("Gradient descent is general: whenever you can compute an error and a delta, it shows how to move "
                      "the weights to reduce the error.", C(5, 98)),
                ],
                "terms": [T("Derivative", "How much the error changes when you nudge a weight. Its slope."),
                          T("Delta", "pred − goal: how much and in which direction you missed."),
                          T("Alpha", "Learning rate. Too big diverges, too small crawls."),
                          T("Mini-batch", "Average the updates over a small batch of examples.")],
            },
            {
                "id": "activations", "num": "3.4", "sym": "Ac", "src": "book",
                "title": "Discuss different neuron activation functions and their purposes",
                "short": "Activation functions",
                "tldr": "A function applied to each neuron's weighted sum. It adds the non-linearity that makes deep "
                        "networks more powerful than one layer, and shapes the output: probability, class or raw number.",
                "cites": ["Ch 6 · p 121–123", "Ch 9 · p 162–174"],
                "body": [
                    H("Why they're needed"),
                    P("Two weighted sums in a row can always be replaced by a single one (1 × 10 × 2 = 5 × 20). So "
                      "without activations, a three-layer network can do nothing a two-layer network can't.",
                      C(6, "121–122")),
                    P("relu fixes this by switching a neuron off whenever its value would be negative. Now a neuron can "
                      "be correlated with an input <i>only sometimes</i>, which Trask calls conditional or 'sometimes' "
                      "correlation.", C(6, 123)),
                    FIG(activations(), "The three standard hidden-layer activations " + C(9, 165)),
                    H("What makes a good activation"),
                    UL("Continuous, with an output for every input " + C(9, 162),
                       "Monotonic: always increasing or always decreasing (preferred, not strictly needed) " + C(9, 163),
                       "Non-linear: it must bend, so one input can change how much the neuron listens to the others "
                       + C(9, 164),
                       "Cheap to compute, along with its derivative " + C(9, 164)),
                    TBL(["Function", "Output range", "Typical use", "Book"], [
                        ["<b>relu</b> = max(0, x)", "0 to ∞", "hidden layers: simple and fast", C(6, 123)],
                        ["<b>sigmoid</b> = 1 / (1 + e<sup>−x</sup>)", "0 to 1", "yes/no probabilities, output layer",
                         C(9, "165–166")],
                        ["<b>tanh</b>", "−1 to 1", "hidden layers; allows negative correlation", C(9, 165)],
                        ["<b>softmax</b>", "0 to 1, all sum to 1", "'which one?' outputs, e.g. which digit",
                         C(9, "167–169")],
                        ["<b>none</b> (linear)", "any number", "predicting raw values such as a temperature", C(9, 166)],
                    ]),
                    H("Choosing the output layer"),
                    P("Three cases: predict raw values (no activation), independent yes/no probabilities (sigmoid), or "
                      "one label out of many (softmax). Softmax raises e to the power of each value and divides by the "
                      "total, so the more likely one label is, the less likely all the others are.", C(9, "166–169")),
                    P("During backpropagation, the delta is multiplied by the activation's slope at that point. For relu "
                      "the slope is 1 if the neuron was on and 0 if it was off.", C(9, "172–173")),
                ],
                "terms": [T("relu", "Negative → 0, positive passes through. Default for hidden layers."),
                          T("sigmoid", "Squashes anything into 0–1; read it as a probability."),
                          T("tanh", "Like sigmoid but −1 to 1."),
                          T("softmax", "Turns a layer into probabilities that add up to 1."),
                          T("Non-linearity", "The bend that lets stacked layers learn more.")],
            },
            {
                "id": "regression", "num": "3.5", "sym": "Rg", "src": "mixed",
                "title": "Create regression models: linear regression with Scikit-Learn, and a neural network for "
                         "similar problems",
                "short": "Regression",
                "tldr": "Regression predicts a number. Scikit-Learn's LinearRegression fits a straight line in one "
                        "call; a neural network with no output activation does the same job by gradient descent, and can "
                        "bend once it has hidden layers.",
                "cites": ["Ch 4 · p 50, 76", "Ch 5 · p 80–82", "Ch 9 · p 166"],
                "body": [
                    P("Regression means predicting a continuous number, such as a price or a temperature. Trask's chapter "
                      "4 network is already a tiny regression model: it learns a weight so that input × weight hits a "
                      "target number (0.8), by minimising squared error.", C(4, "50, 76")),
                    P("For a network that predicts raw values, use <b>no activation</b> on the output layer, because "
                      "sigmoid or tanh would squash every prediction into 0–1.", C(9, 166)),
                    X(H("Linear regression with Scikit-Learn"),
                      P("Linear regression fits y = w·x + b by finding the weights with the lowest mean squared error. "
                        "Scikit-Learn solves this directly, with no step-by-step gradient descent."),
                      CODE("""
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

X, y = make_regression(n_samples=200, n_features=3, noise=10, random_state=0)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

model = LinearRegression().fit(X_train, y_train)   # learn w and b
pred = model.predict(X_test)
print(model.coef_, model.intercept_)               # the learned weights and bias
print("MSE", mean_squared_error(y_test, pred), "R2", r2_score(y_test, pred))
"""),
                      P("<code>fit</code> learns the weights, <code>predict</code> uses them. R² = 1.0 is a perfect fit; "
                        "0 is no better than always predicting the mean.")),
                    X(H("The same problem with a neural network (Trask's method)"),
                      CODE("""
import numpy as np
np.random.seed(0)
weights = np.random.rand(3) * 0.1
alpha = 0.01
for epoch in range(100):
    for x, target in zip(X_train, y_train):
        pred = x.dot(weights)              # weighted sum, no output activation
        delta = pred - target
        weights -= alpha * delta * x       # gradient descent with many inputs (Ch 5)
test_pred = X_test.dot(weights)
print("MSE", np.mean((test_pred - y_test) ** 2))
"""),
                      P("This is a one-layer network, so it can only draw a straight line too. Add a hidden layer with "
                        "relu (see 3.7) and it can fit curves."), tag="Not in Trask · uses the Ch 4–5 method"),
                    X(TBL(["", "LinearRegression", "Neural network"], [
                        ["How it learns", "solves the least-squares equations directly", "gradient descent, many small steps"],
                        ["Shape it can fit", "straight line / flat plane", "curves, once it has hidden layers"],
                        ["Good for", "small tabular data; readable coefficients", "non-linear patterns, lots of data"],
                    ])),
                ],
                "terms": [T("Regression", "Predicting a number rather than a category."),
                          T("Mean squared error", "Average of (prediction − truth)²."),
                          T("R² score", "Share of the variation explained; 1.0 is perfect.", True),
                          T("Coefficient", "A learned weight in linear regression.", True)],
            },
            {
                "id": "classification", "num": "3.6", "sym": "Cl", "src": "mixed",
                "title": "Create classification models: support vector classifier with Scikit-Learn, and a neural "
                         "network for similar problems",
                "short": "Classification",
                "tldr": "Classification predicts a category. A support vector classifier draws the widest possible "
                        "boundary between classes; a neural network learns class probabilities with sigmoid or softmax.",
                "cites": ["Ch 5 · p 94", "Ch 6 · p 100", "Ch 8 · p 146–148", "Ch 9 · p 167–174"],
                "body": [
                    P("Trask's classification problems: the streetlight (walk or stop, from three lights) and MNIST "
                      "(which digit 0–9, from 784 pixel values).", C(6, 100), C(5, 94)),
                    P("For one label out of many, use softmax on the output layer and pick the class with the highest "
                      "probability. Accuracy = correct predictions ÷ total, measured on the test set.",
                      C(9, "167–169"), C(8, 148)),
                    X(H("Support vector classifier (SVC) with Scikit-Learn"),
                      FIG(svm(), "The SVC picks the boundary with the widest gap to the nearest points of each class"),
                      P("An SVC finds the boundary that separates the classes with the widest possible <b>margin</b>. "
                        "Only the points closest to it, the <b>support vectors</b>, decide where it goes. With a "
                        "<b>kernel</b> (e.g. RBF) it can draw curved boundaries. <code>C</code> trades margin width "
                        "against training mistakes: small C = wider, more tolerant margin; large C = fits the training "
                        "data more tightly."),
                      CODE("""
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

X, y = load_digits(return_X_y=True)                # 8x8 digit images: a mini MNIST
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)
scaler = StandardScaler().fit(X_train)             # scale using training data only
X_train, X_test = scaler.transform(X_train), scaler.transform(X_test)

svc = SVC(kernel="rbf", C=10).fit(X_train, y_train)
print("SVC accuracy", svc.score(X_test, y_test))
""")),
                    X(H("The same problem with a neural network"),
                      CODE("""
from sklearn.neural_network import MLPClassifier
nn = MLPClassifier(hidden_layer_sizes=(64,), activation="relu", max_iter=500, random_state=0)
nn.fit(X_train, y_train)                           # backprop + softmax output, like Ch 8-9
print("NN accuracy", nn.score(X_test, y_test))
"""),
                      P("Trask builds this from scratch in NumPy: 784 inputs → relu/tanh hidden layer → 10 softmax "
                        "outputs, with dropout and mini-batches " + C(8, "146–158") + " " + C(9, 174) + "."),
                      tag="Not in Trask · Scikit-Learn version of the Ch 8–9 network"),
                    X(TBL(["", "SVC", "Neural network"], [
                        ["Decision rule", "the widest-margin boundary", "layers of weighted sums + activations"],
                        ["Output", "a class (probabilities optional)", "class probabilities (softmax)"],
                        ["Data size", "great on small to medium data", "shines with lots of data (images, text)"],
                        ["Settings to tune", "C, kernel, gamma", "layers, layer size, alpha, epochs, dropout"],
                    ])),
                ],
                "terms": [T("Classifier", "A model that outputs a category."),
                          T("Accuracy", "Correct ÷ total, on the test set."),
                          T("Margin", "Gap between the boundary and the nearest points.", True),
                          T("Support vectors", "The few points that fix the SVC boundary.", True),
                          T("Kernel trick", "Lets an SVC draw curved boundaries.", True)],
            },
            {
                "id": "deepnet", "num": "3.7", "sym": "Dn", "src": "book",
                "title": "Describe the full structure of a basic deep neural network",
                "short": "A basic deep network",
                "tldr": "Input layer → weights → hidden layer with an activation → weights → output layer. Forward "
                        "propagation makes the prediction; backpropagation sends the error back to update every weight.",
                "cites": ["Ch 6 · p 100–131", "Ch 8 · p 153–155", "Ch 9 · p 166"],
                "body": [
                    FIG(net([3, 4, 1], ["light 1", "light 2", "light 3"], ["walk?"],
                            ["layer_0", "layer_1 (relu)", "layer_2"], back=True),
                        "Trask's first deep network: the streetlight problem " + C(6, 125)),
                    TBL(["Part", "What it is", "Book"], [
                        ["<b>layer_0</b> (input)", "one node per input value (3 lights, or 784 pixels)", C(6, 102)],
                        ["<b>weights_0_1</b>", "matrix connecting input to hidden layer", C(6, 125)],
                        ["<b>layer_1</b> (hidden)", "weighted sums through relu: new 'intermediate datasets'",
                         C(6, "123, 131")],
                        ["<b>weights_1_2</b>", "matrix connecting hidden layer to output", C(6, 125)],
                        ["<b>layer_2</b> (output)", "the prediction; activation chosen for the task", C(9, 166)],
                    ]),
                    H("Forward propagation"),
                    EQ("layer_1 = relu(layer_0 · weights_0_1)", "layer_2 = layer_1 · weights_1_2"),
                    H("Backpropagation"),
                    P("The output delta is passed backwards through weights_1_2: each hidden node is blamed in "
                      "proportion to its weight. It's then multiplied by relu's slope (0 if the node was off). Finally "
                      "every weight moves by alpha × its input × its delta.", C(6, "119–120, 126–129")),
                    EQ("layer_2_delta = layer_2 − goal",
                       "layer_1_delta = (layer_2_delta · weights_1_2ᵀ) × relu′(layer_1)",
                       "weights_1_2 −= alpha × layer_1ᵀ · layer_2_delta",
                       "weights_0_1 −= alpha × layer_0ᵀ · layer_1_delta"),
                    CODE("""
import numpy as np
np.random.seed(1)
relu = lambda x: (x > 0) * x            # negative -> 0
relu2deriv = lambda x: x > 0            # slope: 1 if on, 0 if off

streetlights = np.array([[1, 0, 1], [0, 1, 1], [0, 0, 1], [1, 1, 1]])
walk_vs_stop = np.array([[1, 1, 0, 0]]).T
alpha, hidden_size = 0.2, 4
weights_0_1 = 2 * np.random.random((3, hidden_size)) - 1
weights_1_2 = 2 * np.random.random((hidden_size, 1)) - 1

for iteration in range(60):
    for i in range(len(streetlights)):
        layer_0 = streetlights[i:i+1]
        layer_1 = relu(layer_0.dot(weights_0_1))                 # forward
        layer_2 = layer_1.dot(weights_1_2)
        layer_2_delta = layer_2 - walk_vs_stop[i:i+1]            # compare
        layer_1_delta = layer_2_delta.dot(weights_1_2.T) * relu2deriv(layer_1)   # backprop
        weights_1_2 -= alpha * layer_1.T.dot(layer_2_delta)      # learn
        weights_0_1 -= alpha * layer_0.T.dot(layer_1_delta)
""", "Adapted from Ch 6 p 130 (same network, written with the minus-sign convention)."),
                    H("Why depth matters"),
                    P("No single pixel tells you whether there's a cat; only combinations of pixels do. Hidden layers "
                      "build intermediate features (an ear, an eye) that do correlate with the answer.", C(6, 131)),
                    P("Big networks also need regularisation to generalise. Dropout randomly switches off hidden neurons "
                      "during training, so the network acts like many small networks averaged together.",
                      C(8, "153–155")),
                ],
                "terms": [T("Layer", "A vector of node values; weights connect consecutive layers."),
                          T("Backpropagation", "Passing the delta backwards to find each weight's share of the blame."),
                          T("relu′ (derivative)", "1 where the node was on, 0 where it was off."),
                          T("Dropout", "Randomly zero neurons while training, to reduce overfitting.")],
            },
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "id": "su4", "code": "SU4", "folder": "su4-cnn", "h": 155, "c": 0.13,
        "title": "Convolutional neural networks", "kicker": "Study unit 4",
        "chapters": "Trask chapter 10, plus standard CNN practice",
        "lede": "Where CNNs are used, what a convolutional layer does, and what a pooling layer does. Linked to my "
                "group project, which classifies gravitational-wave glitch spectrograms.",
        "outcomes": [
            {
                "id": "applications", "num": "4.1", "sym": "Ap", "src": "mixed",
                "title": "Discuss the application areas of convolutional neural networks",
                "short": "Where CNNs are used",
                "tldr": "CNNs suit grid-shaped data where the same pattern can appear anywhere: images first, but also "
                        "spectrograms, video, medical scans, and 1-D signals such as audio or text.",
                "cites": ["Ch 10 · p 177–179, 185"],
                "body": [
                    P("Trask introduces CNNs for image recognition (MNIST digits): first learn edges and corners, then "
                      "the shapes built from them.", C(10, "177–179")),
                    P("The key property is <b>reusing weights</b>. You need the same knowledge (what a line looks like) "
                      "in every part of the image. Sharing one small set of weights across all positions means the "
                      "network learns it once, has far fewer parameters, and overfits less.", C(10, "178, 185")),
                    X(TBL(["Area", "Example", "Why a CNN fits"], [
                        ["Image classification", "photos, handwritten digits", "local patterns anywhere in the image"],
                        ["Detection and segmentation", "self-driving cars, tumours in scans",
                         "must find where patterns are, not just name them"],
                        ["Medical imaging", "X-rays, MRI, skin-lesion photos", "small local features matter"],
                        ["Spectrograms", "speech commands, music tagging, <b>Gravity Spy glitches</b> (my SU4 project)",
                         "sound as a time × frequency image"],
                        ["Video", "action recognition", "2-D convolution per frame, or 3-D over time"],
                        ["1-D signals and text", "ECG, sensor data, sentence classification",
                         "patterns repeat along a sequence"],
                    ])),
                    MINE("SU4 group project: a custom CNN, a pretrained EfficientNetV2-S and a Swin transformer "
                         "classifying LIGO glitch spectrograms into 22 classes", "su4-cnn/README.md"),
                ],
                "terms": [T("Weight sharing", "One kernel's weights reused at every position."),
                          T("Feature", "A learned pattern: edge, corner, texture, shape."),
                          T("Spectrogram", "Sound or signal drawn as a time × frequency image.", True)],
            },
            {
                "id": "convlayer", "num": "4.2", "sym": "Cv", "src": "mixed",
                "title": "Discuss the function of a convolutional layer",
                "short": "The convolutional layer",
                "tldr": "Instead of one big layer connecting every pixel to every output, a convolutional layer slides "
                        "many small kernels (e.g. 3×3) over the image, making a prediction at every position.",
                "cites": ["Ch 10 · p 179–184"],
                "body": [
                    FIG(conv(), "A diagonal-line kernel lights up where the image has a diagonal line " + C(10, "179–180")),
                    P("A convolutional <b>kernel</b> is a tiny linear layer: usually fewer than 25 inputs and one output. "
                      "It predicts at one position, moves one pixel to the right, predicts again, and so on across and "
                      "down the image.", C(10, 179)),
                    P("The result is a smaller grid of predictions: an 8×8 image with a 3×3 kernel gives 6×6. A layer "
                      "usually has many kernels, each learning a different feature; one fires on horizontal lines, "
                      "another on diagonals.", C(10, "179–180")),
                    EQ("output size = input size − kernel size + 1 &nbsp;&nbsp;&nbsp;(8 − 3 + 1 = 6)"),
                    P("In NumPy, Trask cuts every kernel-sized patch out of the images, stacks the patches, and multiplies "
                      "them all by the kernel weights in one dot product: the same weights reused at every position.",
                      C(10, "181–184")),
                    X(P("Terms you'll see elsewhere: <b>stride</b> (how many pixels the kernel moves each step; stride 2 "
                        "halves the output), <b>padding</b> (a border of zeros so the output keeps the input's size), "
                        "and <b>channels</b> (a colour image has 3 input channels; a layer with 16 kernels outputs 16 "
                        "feature maps)."),
                      EQ("output = (input − kernel + 2 × padding) / stride + 1"),
                      CODE("""
import torch.nn as nn
conv = nn.Conv2d(in_channels=1, out_channels=16, kernel_size=3, padding=1)   # 16 kernels, 3x3
"""), tag="Not in Trask"),
                ],
                "terms": [T("Kernel (filter)", "A small set of weights slid over the input."),
                          T("Feature map", "A kernel's grid of outputs."),
                          T("Stride", "Step size of the slide.", True),
                          T("Padding", "Zeros around the edge to keep the size.", True)],
            },
            {
                "id": "pooling", "num": "4.3", "sym": "Pl", "src": "mixed",
                "title": "Discuss the function of a pooling layer",
                "short": "The pooling layer",
                "tldr": "Pooling combines several values into one, usually the maximum. It keeps the strongest signals "
                        "and shrinks the data.",
                "cites": ["Ch 10 · p 180"],
                "body": [
                    P("In Trask's example, four 3×3 kernels each produce a 6×6 grid for the same image. Pooling combines "
                      "them into one 6×6 grid: <b>sum pooling</b> adds them, <b>mean pooling</b> averages them, and "
                      "<b>max pooling</b> keeps the largest value at each position. Max pooling is the most popular.",
                      C(10, 180)),
                    X(P("In most CNNs, pooling is applied <b>across space</b> within each feature map: a 2×2 window with "
                        "stride 2 keeps only the largest value in each 2×2 block, halving the height and width."),
                      FIG(pool(), "2×2 max pooling: each colour block becomes one number"),
                      UL("<b>Less data</b>: less computation and fewer weights in later layers",
                         "<b>Small shifts don't matter</b> (translation invariance): if a feature moves a pixel, the "
                         "maximum often stays the same",
                         "<b>Wider view</b>: each later kernel covers a bigger part of the original image",
                         "<b>Nothing to learn</b>: pooling has no weights"),
                      P("A typical CNN repeats conv → relu → pool, then flattens the result into ordinary dense layers "
                        "for the final classification. In PyTorch: <code>nn.MaxPool2d(2)</code>.")),
                ],
                "terms": [T("Max pooling", "Keep the largest value in each window."),
                          T("Mean / sum pooling", "Average or add the values instead."),
                          T("Translation invariance", "The output barely changes if the input shifts a little.", True)],
            },
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "id": "su57", "code": "SU5–7", "folder": "su5-7-llm-agents", "h": 340, "c": 0.15,
        "title": "Transfer learning, LLMs and agents", "kicker": "Study units 5, 6 and 7",
        "chapters": "Trask chapters 2, 11, 12 and 14 for the foundations; the rest is from other sources",
        "lede": "Labelled and unlabelled data, clustering, semi-supervised learning, transfer learning, and how large "
                "language models work, are used and are fine-tuned. Much of this postdates the 2019 book, so most of "
                "this page carries the 'Not in Trask' marker.",
        "outcomes": [
            {
                "id": "labelled", "num": "5.1", "sym": "Lb", "src": "mixed",
                "title": "Recognise the difference between using labelled and unlabelled data",
                "short": "Labelled vs unlabelled",
                "tldr": "Labelled data comes with the right answer for each example (image + 'cat'). Unlabelled data is "
                        "just the raw examples. Labels make supervised learning possible but are expensive to get.",
                "cites": ["Ch 2 · p 12–13", "Ch 11 · p 190–191, 201"],
                "body": [
                    P("Supervised learning needs two datasets: the inputs and the matching outputs, which are the "
                      "<b>labels</b>. Unsupervised learning has only inputs and no right answer to copy.",
                      C(2, "12–13")),
                    P("Book example: IMDB movie reviews come with a star rating, so each review can be labelled positive "
                      "or negative. That makes it supervised NLP.", C(11, "190–191")),
                    P("Trask's fill-in-the-blank network trains on plain text with no human labels at all: it hides a "
                      "word and learns to predict it. The text supplies its own labels.", C(11, 201)),
                    X(P("This trick is called <b>self-supervised learning</b>, and it's how LLMs are pretrained on huge "
                        "amounts of unlabelled text."),
                      TBL(["", "Labelled", "Unlabelled"], [
                          ["What it is", "(input, answer) pairs", "inputs only"],
                          ["Cost", "expensive: people must annotate", "cheap and plentiful (web text, logs, images)"],
                          ["Typical use", "classification, regression", "clustering, dimensionality reduction, anomaly "
                                                                       "detection, pretraining"],
                          ["Example", "X-rays marked 'fracture' / 'no fracture'", "a million unmarked X-rays"],
                      ])),
                ],
                "terms": [T("Label", "The correct answer attached to an example."),
                          T("Annotation", "People adding labels by hand; slow and costly.", True),
                          T("Self-supervised", "Labels created from the data itself (hide a word, predict it).", True)],
            },
            {
                "id": "nature", "num": "5.2", "sym": "Nd", "src": "mixed",
                "title": "Understand the nature of data and how different techniques apply to unlabelled data than to "
                         "labelled data",
                "short": "Data decides the technique",
                "tldr": "What you can do depends on what you have. With labels you can learn to predict them. Without "
                        "labels you can only find structure (groups, main directions of variation, outliers) or invent "
                        "labels from the data itself.",
                "cites": ["Ch 2 · p 12–13, 17", "Ch 10 · p 178", "Ch 12 · p 210"],
                "body": [
                    P("Supervised learning turns what you know into what you want to know. Unsupervised learning finds "
                      "groups that you then have to interpret; the algorithm never tells you what a cluster means.",
                      C(2, "12–13")),
                    P("The two work together: unsupervised learning is often done to help build a better supervised "
                      "model.", C(2, 12)),
                    P("The type of data matters too: images have spatial structure, which suits convolutions; text is a "
                      "variable-length sequence of words, which suits embeddings and recurrent layers.", C(10, 178),
                      C(12, 210)),
                    X(TBL(["What you have", "Techniques", "Example"], [
                        ["Labels that are numbers", "regression", "predict a house price"],
                        ["Labels that are categories", "classification (SVC, neural nets, trees)", "spam or not spam"],
                        ["No labels", "clustering (k-means, DBSCAN)", "customer segments"],
                        ["No labels", "dimensionality reduction (PCA, t-SNE, UMAP)", "plot 784-pixel images in 2-D"],
                        ["No labels", "anomaly detection", "flag unusual card transactions"],
                        ["No labels", "self-supervised pretraining", "train an LLM on web text"],
                        ["A few labels, lots unlabelled", "semi-supervised learning", "label 1% of images, use all"],
                        ["Labels from another domain", "transfer learning", "reuse an ImageNet model for spectrograms"],
                    ]),
                      P("Also check: how much data there is (deep nets need lots), its quality and noise, class balance "
                        "(with 99% 'normal', accuracy is misleading), and whether examples are independent or a sequence.")),
                ],
                "terms": [T("Structure", "Patterns in unlabelled data: groups, directions, outliers."),
                          T("Dimensionality reduction", "Squash many features into a few, keeping the shape.", True),
                          T("Anomaly detection", "Find the points that don't fit the rest.", True)],
            },
            {
                "id": "clustering", "num": "5.3", "sym": "Cu", "src": "mixed",
                "title": "Perform clustering operations on unlabelled data",
                "short": "Clustering",
                "tldr": "Clustering puts similar unlabelled points into groups. k-means is the classic: pick k centres, "
                        "assign every point to the nearest one, move each centre to the middle of its points, repeat.",
                "cites": ["Ch 2 · p 13, 17", "Ch 11 · p 199–203"],
                "body": [
                    P("Clustering turns a list of datapoints into a list of cluster labels (1–10 for 10 clusters). The "
                      "labels are just numbers; you work out what each group means: puppies and kittens = 'cute', "
                      "pizza and burgers = 'delicious'.", C(2, 13)),
                    P("An unsupervised parametric model outputs, for each group, the probability that a datapoint belongs "
                      "to it (e.g. 94% group 1, 1% group 2, 5% group 3).", C(2, 17)),
                    P("Clusters also appear inside neural networks. After training on movie reviews, similar words get "
                      "similar embedding vectors, and you can list a word's nearest neighbours ('terrible' → 'dull', "
                      "'boring', 'disappointing'). What the words cluster by depends on the training task.",
                      C(11, "199–203")),
                    X(H("k-means, step by step"),
                      OL("Choose k, the number of clusters.", "Place k centres (centroids), e.g. at random points.",
                         "<b>Assign</b>: each point joins its nearest centre.",
                         "<b>Update</b>: move each centre to the mean of its points.",
                         "Repeat steps 3–4 until nothing changes."),
                      FIG(kmeans(), "k-means with k = 3"),
                      CODE("""
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

X, _ = make_blobs(n_samples=300, centers=3, random_state=42)    # throw the labels away
X = StandardScaler().fit_transform(X)                           # distances need equal scales
for k in range(2, 7):                                           # which k fits best?
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    print(k, round(km.inertia_, 1), round(silhouette_score(X, km.labels_), 3))
labels = KMeans(n_clusters=3, n_init=10, random_state=0).fit_predict(X)
"""),
                      P("<b>Choosing k</b>: plot the inertia (total squared distance to the centres) for k = 1…10 and "
                        "look for the 'elbow', or pick the k with the highest silhouette score. <b>Other methods</b>: "
                        "DBSCAN finds clusters of any shape and marks outliers as noise; hierarchical clustering builds "
                        "a tree of merges.")),
                ],
                "terms": [T("Cluster", "A group of points that are close to each other."),
                          T("Centroid", "The centre (mean) of a cluster.", True),
                          T("Elbow / silhouette", "Ways to choose the number of clusters.", True),
                          T("Embedding neighbours", "Words with similar vectors; a natural clustering.")],
            },
            {
                "id": "semi", "num": "5.4", "sym": "Ss", "src": "extra",
                "title": "Understand and use tools that use semi-supervised learning",
                "short": "Semi-supervised learning",
                "tldr": "Use a small labelled set together with a large unlabelled one. The model labels the unlabelled "
                        "data itself (self-training) or spreads labels to similar points (label propagation).",
                "cites": ["Ch 2 · p 12 (background only)"],
                "body": [
                    P("Trask doesn't cover semi-supervised learning. He does note that unsupervised learning is usually "
                      "done to help supervised learning, which is the idea semi-supervised methods build on.", C(2, 12)),
                    X(P("Labelling is slow and costly; unlabelled data is cheap. Semi-supervised learning sits between "
                        "supervised and unsupervised, and assumes that points close together (or in the same cluster) "
                        "probably share a label."),
                      H("Self-training (pseudo-labelling)"),
                      OL("Train a model on the labelled data.", "Predict the unlabelled data.",
                         "Keep the predictions it's very confident about (e.g. ≥ 90%) as <b>pseudo-labels</b>.",
                         "Retrain on labelled + pseudo-labelled data, and repeat."),
                      H("Label propagation and spreading"),
                      P("Connect similar points in a graph; the known labels spread along the connections to their "
                        "neighbours, like ink in water."),
                      CODE("""
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.semi_supervised import SelfTrainingClassifier, LabelSpreading
from sklearn.svm import SVC

X, y = load_digits(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
rng = np.random.RandomState(0)
y_partial = y_train.copy()
y_partial[rng.rand(len(y_partial)) < 0.9] = -1      # hide 90% of the labels (-1 = unlabelled)

self_train = SelfTrainingClassifier(SVC(probability=True, gamma=0.001), threshold=0.9)
self_train.fit(X_train, y_partial)
print("self-training  ", self_train.score(X_test, y_test))

spread = LabelSpreading(kernel="knn", n_neighbors=7).fit(X_train, y_partial)
print("label spreading", spread.score(X_test, y_test))
"""),
                      H("Tools"),
                      TBL(["Tool", "What it does"], [
                          ["scikit-learn <code>SelfTrainingClassifier</code>", "wraps any classifier that gives "
                                                                               "probabilities; adds pseudo-labels in rounds"],
                          ["scikit-learn <code>LabelPropagation</code> / <code>LabelSpreading</code>",
                           "graph-based; unlabelled points are marked −1"],
                          ["Snorkel", "weak supervision: write labelling rules, combine their votes"],
                          ["Cleanlab", "finds labels that are probably wrong"],
                          ["LLM training", "pretrain on unlabelled text, then fine-tune on a small labelled set: "
                                           "the same idea at a huge scale"],
                      ]),
                      P("<b>Watch out</b>: confident but wrong pseudo-labels reinforce themselves (confirmation bias). "
                        "Keep the threshold high and always check accuracy on a labelled test set.")),
                ],
                "terms": [T("Pseudo-label", "A label the model guessed and is confident about.", True),
                          T("Confidence threshold", "Only keep guesses above this probability.", True),
                          T("Label propagation", "Labels spread to similar neighbours in a graph.", True)],
            },
            {
                "id": "transfer", "num": "5.5", "sym": "Tl", "src": "mixed",
                "title": "Understand and use transfer learning to apply a model trained in one domain to a different "
                         "domain",
                "short": "Transfer learning",
                "tldr": "Reuse what a model learned on one task as the starting point for another: keep (freeze) the "
                        "early layers, replace and retrain the last ones, then optionally fine-tune everything with a "
                        "small learning rate.",
                "cites": ["Ch 3 · p 26", "Ch 5 · p 88", "Ch 10 · p 185", "Ch 11 · p 194, 203"],
                "body": [
                    P("Trask doesn't use the term, but the ingredients are in the book:"),
                    UL("Knowledge lives in the weights, so weights can be copied into another network. " + C(3, 26),
                       "A weight can be frozen (not updated) while the rest keep learning. " + C(5, 88),
                       "Early CNN layers learn general features (lines, edges, corners) that any image task needs. "
                       + C(10, 185),
                       "Word embeddings learned on one task capture meaning that can be reused, and what they capture "
                       "depends on the task they were trained on. " + C(11, "194, 203")),
                    X(H("How it works"),
                      transfer(),
                      OL("Start from a model pretrained on a big dataset (ImageNet photos; web text for LLMs).",
                         "Remove its output layer and add a new one for your classes.",
                         "<b>Feature extraction</b>: freeze the pretrained layers and train only the new head.",
                         "<b>Fine-tuning</b>: then unfreeze some or all layers and train with a small learning rate, "
                         "so the useful features are adjusted rather than wiped out."),
                      P("<b>Why bother</b>: you need far less data and compute, and usually get better accuracy than "
                        "training from scratch on a small dataset. <b>Domain shift</b>: the further the new domain is "
                        "from the original (everyday photos → spectrograms), the more layers you may need to retrain."),
                      CODE("""
import timm
# EfficientNetV2-S pretrained on ImageNet; timm swaps the 1000-class head for a new 22-class one
model = timm.create_model("tf_efficientnetv2_s", pretrained=True, num_classes=22)
# fine-tune with a small learning rate (1e-4): a large one washes out the pretrained features
"""), P("This is exactly what our SU4 group project does in <code>models/transfer_cnn.py</code>, next to a "
        "CNN trained from scratch for comparison. For LLMs it's the same idea: a model pretrained on general text "
        "is fine-tuned on one domain (see 5.8).")),
                    MINE("Gravity Spy transfer model (EfficientNetV2-S, ImageNet → LIGO spectrograms)",
                         "su4-cnn/group-repo/models/transfer_cnn.py"),
                ],
                "terms": [T("Pretrained model", "A model already trained on a large dataset.", True),
                          T("Freezing", "Not updating some weights during training."),
                          T("Fine-tuning", "Continuing training on the new task with a small learning rate.", True),
                          T("Domain shift", "How different the new data is from the original.", True)],
            },
            {
                "id": "llm", "num": "5.6", "sym": "Lm", "src": "mixed",
                "title": "Understand the basic building blocks and operation of Large Language Models",
                "short": "How LLMs work",
                "tldr": "An LLM turns text into tokens, tokens into embedding vectors, mixes them through stacked "
                        "transformer layers (attention + feed-forward), and ends with a softmax over the vocabulary to "
                        "predict the next token. Repeat to generate text.",
                "cites": ["Ch 9 · p 169", "Ch 11 · p 191–207", "Ch 12 · p 210–227", "Ch 13 · p 232–260",
                          "Ch 14 · p 266–280"],
                "body": [
                    flow([("Text", "“The cat sat”"), ("Tokens", "split into pieces with ids"),
                          ("Embeddings", "a learned vector per token"),
                          ("Transformer ×N", "attention + feed-forward", "x"),
                          ("Softmax", "probability for every token in the vocabulary"),
                          ("Next token", "pick one, append, repeat")], "generation: feed the new token back in"),
                    TBL(["Building block", "What it does", "In Trask"], [
                        ["Vocabulary and tokens", "text split into pieces, each with an index",
                         "words " + C(11, "191–192") + ", characters " + C(14, 266)],
                        ["Embedding layer", "looks up a learned vector for each token", C(11, 194) + " " + C(13, "255–257")],
                        ["Similar meaning → similar vector", "king − man + woman ≈ queen", C(11, "199–207")],
                        ["Next-token prediction", "predict the next word or character from the previous ones",
                         C(12, "222–227") + " " + C(14, 266)],
                        ["Softmax and cross-entropy", "scores → probabilities over the vocabulary; the training loss",
                         C(9, 169) + " " + C(13, 258)],
                        ["Sequence memory (RNN, LSTM)", "carry a hidden state across time; LSTM gates stop vanishing "
                                                        "gradients", C(12, 210) + " " + C(14, "272–275")],
                        ["Frameworks and autograd", "automatic gradients, needed for huge models", C(13, "232–234")],
                        ["x", "Self-attention, transformers", "every token looks at every other token", "—"],
                        ["x", "Pretrain → fine-tune → RLHF", "how chat models are made", "—"],
                    ]),
                    P("Trask's Shakespeare model is a small language model: given the characters so far, predict the next "
                      "one, sample it, feed it back in.", C(14, "266–271")),
                    X(H("What changed: attention and transformers"),
                      P("RNNs read one token at a time and squeeze everything into one hidden state, which forgets over "
                        "long texts and can't be parallelised. A <b>transformer</b> (2017) drops recurrence. In each "
                        "<b>self-attention</b> layer, every token makes a query, a key and a value vector; it compares "
                        "its query with every token's key, turns the scores into weights with softmax, and takes a "
                        "weighted sum of the values. That's the SU2 weighted sum again, with the weights worked out on "
                        "the fly."),
                      EQ("Attention(Q, K, V) = softmax(Q · Kᵀ / √d) · V"),
                      UL("<b>Context window</b>: how many tokens the model can attend to at once. Ollama loads models "
                         "with 4,096 tokens by default; agents need far more (see my local-LLM notes).",
                         "<b>Positional information</b> is added to the embeddings so that word order matters.",
                         "<b>Parameters</b> are the weights: '12B' means 12 billion. <b>Quantisation</b> (e.g. Q4_K_M) "
                         "stores them in about 4 bits each, so a 12B model fits in 12 GB of VRAM.",
                         "<b>Sampling</b>: temperature and top-p control how the next token is picked from the softmax "
                         "probabilities.",
                         "<b>Speculative decoding</b>: a small draft model proposes tokens and the big model checks them "
                         "in one pass. That's why Gemma 4 12B ran at 172 tokens/s on my GPU.",
                         "<b>Sliding-window attention</b>: some layers only look at the most recent tokens, to save "
                         "memory."),
                      P("Our SU4 group project also has a Swin transformer: attention applied to image patches instead "
                        "of words.")),
                    MINE("My local LLM: Ollama on an RTX 5070, models tried, speeds and context-length findings",
                         "su5-7-llm-agents/local-llm/README.md"),
                ],
                "terms": [T("Token", "A piece of text (word, part of a word, character) with an id."),
                          T("Embedding", "The learned vector for a token."),
                          T("Language model", "Predicts the next token from the previous ones."),
                          T("Self-attention", "Each token takes a weighted mix of all the others.", True),
                          T("Context window", "The most tokens the model can consider at once.", True)],
            },
            {
                "id": "usellm", "num": "5.7", "sym": "Us", "src": "extra",
                "title": "Use Large Language Models effectively as they exist already",
                "short": "Using LLMs well",
                "tldr": "Pick a model that fits your hardware and task, give it clear instructions and the right "
                        "context, let it use tools, and always check its output.",
                "cites": ["not in the book (2019)"],
                "body": [
                    P("Not covered in Trask: the book predates modern LLMs. This section is based on my own setup and "
                      "general practice."),
                    X(H("Picking a model"),
                      UL("The model plus its context should fit fully in VRAM; spilling into system RAM is much slower.",
                         "Quantised versions (Q4, Q5) trade a little quality for a lot of memory.",
                         "Specialised models (coding, vision, reasoning) beat general ones of the same size at their "
                         "task."),
                      H("Prompting"),
                      UL("Be specific: role, task, constraints, output format, an example.",
                         "Give it the context it needs (files, docs) instead of hoping it knows.",
                         "Break big tasks into steps, and ask for a plan first.",
                         "Use low temperature for facts and code, higher for brainstorming."),
                      H("Beyond prompting"),
                      TBL(["Technique", "What it does"], [
                          ["RAG (retrieval-augmented generation)", "search your own documents and paste the relevant "
                                                                   "parts into the prompt"],
                          ["Tools / function calling", "let the model run code, read files, search the web"],
                          ["Agents", "a loop: plan → act with tools → look at the result → repeat (Codex, Claude Code)"],
                          ["System prompts, Modelfiles", "fixed instructions and settings for every conversation"],
                          ["Fine-tuning", "change the weights when prompting isn't enough (5.8)"],
                      ]),
                      H("Know the limits"),
                      P("LLMs can be confidently wrong (hallucination), have a knowledge cutoff, and lose anything beyond "
                        "their context window. Verify facts, run the code, and review every diff.")),
                    MINE("My system: Ollama + Codex on my own GPU (setup, tests, benchmark)",
                         "su5-7-llm-agents/local-llm/README.md"),
                    MINE("Every model I tried and what I learned", "models/README.md"),
                ],
                "terms": [T("Prompt", "The instructions and context you send.", True),
                          T("RAG", "Fetch relevant documents and add them to the prompt.", True),
                          T("Agent", "An LLM in a loop that can use tools.", True),
                          T("Hallucination", "A confident answer that is wrong.", True)],
            },
            {
                "id": "finetune", "num": "5.8", "sym": "Ft", "src": "extra",
                "title": "Fine-tune a Large Language Model to a specific domain",
                "short": "Fine-tuning an LLM",
                "tldr": "Keep training a pretrained LLM on examples from your domain so its weights shift towards your "
                        "task. LoRA trains small adapter matrices instead of all the weights, which makes it possible "
                        "on one consumer GPU (e.g. with Unsloth).",
                "cites": ["Ch 4 · p 56–76", "Ch 5 · p 88", "Ch 8 · p 150–152 (background)"],
                "body": [
                    P("Fine-tuning is chapter 4's gradient descent applied to a pretrained network: predict, compare with "
                      "the example answer, nudge the weights.", C(4, "56–76"),
                      "LoRA's frozen base weights echo the frozen-weight experiment.", C(5, 88),
                      "And the book's warnings still apply: a small dataset trained for too long gets memorised, so keep "
                      "a validation set.", C(8, "150–152")),
                    X(H("Options"),
                      TBL(["Method", "What is trained", "Memory"], [
                          ["Full fine-tuning", "all the weights", "very high: several copies of the model in memory"],
                          ["LoRA", "small low-rank adapter matrices beside the frozen weights (~0.1–1% of the "
                                   "parameters)", "low"],
                          ["QLoRA", "LoRA on a 4-bit quantised base model", "lowest: a 4–9B model fits on 12 GB"],
                      ]),
                      EQ("W′ = W + B · A &nbsp;&nbsp;&nbsp;(W frozen; only the thin matrices A and B are trained)"),
                      H("Workflow"),
                      OL("<b>Goal</b>: what should the model do better? (answer in my project's style, know ITRI626 "
                         "terms, use my tools correctly)",
                         "<b>Dataset</b>: hundreds to a few thousand instruction → response pairs in the model's chat "
                         "format; hold back ~10% for validation.",
                         "<b>Base model</b> that fits the GPU (a 4–9B model for QLoRA on 12 GB).",
                         "<b>Train</b> LoRA adapters for 1–3 epochs, watching training and validation loss.",
                         "<b>Evaluate</b> against the base model on held-out questions.",
                         "<b>Export</b>: merge the adapters, convert to GGUF, load into Ollama with a Modelfile."),
                      CODE("""
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen3-4B",        # any base model that fits in 12 GB
    max_seq_length=2048,
    load_in_4bit=True,                    # QLoRA: 4-bit base model
)
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=16,           # LoRA rank and scaling
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
)
dataset = load_dataset("json", data_files="my_domain.jsonl", split="train")   # one {"text": ...} per line
trainer = SFTTrainer(
    model=model, tokenizer=tokenizer, train_dataset=dataset,
    args=SFTConfig(per_device_train_batch_size=2, gradient_accumulation_steps=4,
                   num_train_epochs=1, learning_rate=2e-4, output_dir="outputs"),
)
trainer.train()
model.save_pretrained_gguf("my-model", tokenizer, quantization_method="q4_k_m")   # for Ollama
""", "A sketch of the usual Unsloth recipe. Check the Unsloth docs for current model names and arguments.")),
                    MINE("Planned: my Unsloth fine-tune, documented with the other models", "models/README.md"),
                ],
                "terms": [T("LoRA", "Train small adapter matrices, keep the base weights frozen.", True),
                          T("QLoRA", "LoRA on a 4-bit base model, to save memory.", True),
                          T("Epoch", "One full pass over the training data."),
                          T("GGUF", "The model file format Ollama and llama.cpp load.", True)],
            },
        ],
    },
]
