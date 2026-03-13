import numpy as np
from agent.bandit import train

print("Running convergence check...")
model, history = train(epochs=50)

losses = history.history["loss"]
val_losses = history.history["val_loss"]

# Split into first and second half
mid = len(losses) // 2
first_half_avg = np.mean(losses[:mid])
second_half_avg = np.mean(losses[mid:])

# Check convergence criteria
loss_decreased = second_half_avg < first_half_avg
final_loss_acceptable = losses[-1] < 0.01

print("\n--- Convergence Report ---")
print(f"First half avg loss:  {first_half_avg:.6f}")
print(f"Second half avg loss: {second_half_avg:.6f}")
print(f"Final training loss:  {losses[-1]:.6f}")
print(f"Final validation loss: {val_losses[-1]:.6f}")
print(f"Loss decreased across epochs: {loss_decreased}")
print(f"Final loss under threshold:   {final_loss_acceptable}")

if loss_decreased and final_loss_acceptable:
    print("\n Check 2 Passed — Model convergence confirmed")
else:
    print("\n Check 2 Failed — Model not converging correctly")
