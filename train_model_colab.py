"""
AgriWis — Block 3: Disease Classifier Training Script.

RUN THIS ON GOOGLE COLAB (Runtime > Change runtime type > GPU), not locally.
Colab has both GPU and internet access to pull the dataset — your local
machine likely has neither fast enough for this.

Steps to run:
1. Open colab.research.google.com > New notebook
2. Paste this whole file into one cell
3. Runtime > Change runtime type > T4 GPU
4. Run the cell — takes ~20-30 min
5. Download the output file `agriwis_disease_model.keras` at the end
6. Put it in your local agriwis/disease/ folder

Uses transfer learning (MobileNetV2 pretrained on ImageNet) fine-tuned on
PlantVillage — far faster and more accurate than training from scratch
with limited data, and small enough (~14MB) to run inference on CPU later.
"""

# ── Cell 1: Install + get dataset ──
!pip install -q tensorflow tensorflow-datasets

import tensorflow as tf
import tensorflow_datasets as tfds

# PlantVillage dataset, ~54k labeled leaf images across 38 disease/healthy classes
(train_ds, val_ds), ds_info = tfds.load(
    "plant_village",
    split=["train[:85%]", "train[85%:]"],
    as_supervised=True,
    with_info=True,
)

NUM_CLASSES = ds_info.features["label"].num_classes
CLASS_NAMES = ds_info.features["label"].names
IMG_SIZE = 224
BATCH_SIZE = 32

print(f"Classes ({NUM_CLASSES}):", CLASS_NAMES)

# ── Cell 2: Preprocess ──
def preprocess(image, label):
    image = tf.image.resize(image, (IMG_SIZE, IMG_SIZE))
    image = tf.keras.applications.mobilenet_v2.preprocess_input(image)
    return image, label

train_ds = train_ds.map(preprocess).shuffle(1000).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
val_ds = val_ds.map(preprocess).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

# ── Cell 3: Build model (transfer learning) ──
base_model = tf.keras.applications.MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights="imagenet",
)
base_model.trainable = False  # freeze pretrained layers first

model = tf.keras.Sequential([
    base_model,
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(128, activation="relu"),
    tf.keras.layers.Dense(NUM_CLASSES, activation="softmax"),
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

# ── Cell 4: Train (frozen base) ──
history = model.fit(train_ds, validation_data=val_ds, epochs=8)

# ── Cell 5: Fine-tune (unfreeze top layers for a few epochs) ──
base_model.trainable = True
for layer in base_model.layers[:-20]:
    layer.trainable = False

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

history_fine = model.fit(train_ds, validation_data=val_ds, epochs=5)

# ── Cell 6: Evaluate honestly ──
val_loss, val_acc = model.evaluate(val_ds)
print(f"Final validation accuracy: {val_acc:.3f}")
# Report THIS number in your pitch deck, not a guessed one. If it's below
# ~90%, that's fine to state honestly — judges respect real numbers over
# inflated ones.

# ── Cell 7: Save class names + model ──
import json
with open("class_names.json", "w") as f:
    json.dump(CLASS_NAMES, f)

model.save("agriwis_disease_model.keras")

# ── Cell 8: Download both files ──
from google.colab import files
files.download("agriwis_disease_model.keras")
files.download("class_names.json")
