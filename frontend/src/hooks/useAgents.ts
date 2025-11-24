import { useState, useEffect, useRef, useCallback } from 'react';
import { api, getApiKey } from '../utils/api';
import type { Agent, AgentCreate } from '../types';

const POLL_INTERVAL = 2000; // Poll every 2 seconds

export const useAgents = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const apiKey = getApiKey();

  const fetchAgents = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);
      const data = await api.getAllAgents();

      // Only update state if agents have actually changed
      setAgents((prevAgents) => {
        // Check if data is different
        if (prevAgents.length !== data.length) {
          return data;
        }

        // Check if any agent has changed
        const hasChanges = data.some((newAgent) => {
          const prevAgent = prevAgents.find(a => a.id === newAgent.id);
          if (!prevAgent) return true;

          // Compare relevant properties
          return (
            prevAgent.name !== newAgent.name ||
            prevAgent.profile_pic !== newAgent.profile_pic ||
            prevAgent.config_file !== newAgent.config_file
          );
        });

        return hasChanges ? data : prevAgents;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch agents');
      console.error('Failed to fetch agents:', err);
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    // Only fetch if API key is available
    if (!apiKey) {
      setLoading(false);
      return;
    }

    let isActive = true;

    // Initial fetch
    fetchAgents(true);

    // Setup polling using setTimeout to prevent stacking
    const scheduleNextPoll = () => {
      if (!isActive) return;

      pollIntervalRef.current = setTimeout(async () => {
        await fetchAgents(false);
        scheduleNextPoll(); // Schedule next poll after this one completes
      }, POLL_INTERVAL);
    };

    // Start polling
    scheduleNextPoll();

    return () => {
      isActive = false;
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [apiKey, fetchAgents]);

  const createAgent = async (agentData: AgentCreate): Promise<Agent> => {
    try {
      const newAgent = await api.createAgent(agentData);
      setAgents((prev) => [...prev, newAgent]);
      return newAgent;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred';
      setError(message);
      throw err;
    }
  };

  const deleteAgent = async (agentId: number): Promise<void> => {
    try {
      await api.deleteAgent(agentId);
      setAgents((prev) => prev.filter((agent) => agent.id !== agentId));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred';
      setError(message);
      throw err;
    }
  };

  const refreshAgents = () => {
    fetchAgents();
  };

  return {
    agents,
    loading,
    error,
    createAgent,
    deleteAgent,
    refreshAgents,
  };
};
