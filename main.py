import gym
import numpy as np
import torch
import random
import seaborn as sns
from environment import VectorizedEnvWrapper
from reinforcement_learning_policies import CategoricalPolicy, DiagonalGaussianPolicy
from REINFORCE_client import REINFORCE_client
from geom_median.torch import compute_geometric_median  


def main():
    # Initialize the environment
    env = VectorizedEnvWrapper(gym.make("CartPole-v1"), num_envs=32)
    N = env.observation_space.shape[0]
    M = env.action_space.n

    # Create the global model
    global_model = torch.nn.Sequential(
                torch.nn.Linear(N, M),
            ).double()
    global_dict = global_model.state_dict()
    # Copy the global model to create client models
    client_models = [CategoricalPolicy(env, lr=1e-1) for _ in range(10)]
    for model in client_models:
        model.p.load_state_dict(global_model.state_dict())

    # Training loop
    epoch_rewards = []
    for epoch in range(100):
        gradients, rewards = [], []

        # Collect gradients and rewards from each client
        for client_model in client_models:
            grad, reward = REINFORCE_client(env, client_model)
            gradients.append(grad)
            rewards.append(reward)

        # Attack: Sign-flipping
        malicious_clients = random.sample(range(10), 3)
        for client_idx in malicious_clients:
            for grad_idx in range(len(global_model.state_dict())):
                gradients[client_idx][grad_idx] = -2.5*gradients[client_idx][grad_idx]

        # Compute geometric median of gradients
        median_gradient = compute_geometric_median(gradients, weights=None)

        # Update global model
        i=0
        for k in global_dict.keys():
            global_dict[k] = median_gradient.median[i]
            i=i+1
        global_model.load_state_dict(global_dict)


        # Synchronize client models with the global model
        for model in client_models:
            model.p.load_state_dict(global_model.state_dict())

        # Print model parameters for verification
        for key in global_model.state_dict():
            print(key, global_model.state_dict()[key])

        # Store average reward
        epoch_rewards.append(sum(rewards) / len(rewards))

    # Plot reward trends
    fig = sns.lineplot(x=range(len(epoch_rewards)), y=epoch_rewards)
    fig_1 = fig.get_figure()
    fig_1.savefig("out.png")

if __name__ == "__main__":
    main()