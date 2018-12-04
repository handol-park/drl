import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import gym
import tqdm

import util

def train(env: gym.Env, policy_network: nn.Module, n_episodes=1, t_max=1000, clip_epsilon=0.2, gamma=1., alpha=1e-3):
    policy = util.Policy(policy_network)
    optim = torch.optim.Adam(policy_network.parameters(), lr=alpha)

    scores = []

    for _i_episode in range(n_episodes):
        episode = util.run_episode(env, policy, t_max=t_max)
        rewards, observations, actions = [np.vstack(x) for x in zip(*episode)]

        scores.append(np.sum(rewards))
        last_100_score_average = np.mean(scores[-100:])

        if _i_episode % 100 == 0:
            print(f'episode: {_i_episode}\tlast 100 score average: {last_100_score_average}')

        if last_100_score_average > 196.:
            print(f'SOLVED at episode {_i_episode}: last 100 score average: {last_100_score_average} > 195.')
            break

        gammas = gamma ** np.arange(len(episode) - 1)[:, np.newaxis]
        g = np.sum(gammas * rewards[1:])

        actions = torch.as_tensor(actions)
        old_probs = policy.pd(observations[:-1]).probs.gather(dim=1, index=actions[:-1]).detach()

        # PPO reuses a sample trajectory multiple times
        for _ in range(3):
            new_probs = policy.pd(observations[:-1]).probs.gather(dim=1, index=actions[:-1])
            prop_ratio = new_probs / old_probs
            clipped_prop_ratio = prop_ratio.clamp(1. - clip_epsilon, 1. + clip_epsilon)
            surrogate = torch.min(prop_ratio * g, clipped_prop_ratio * g).sum()
            loss = - surrogate
            optim.zero_grad()
            loss.backward()
            optim.step()
        
    return policy, scores
