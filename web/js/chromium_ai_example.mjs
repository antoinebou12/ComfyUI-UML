#!/usr/bin/env node
/**
 * Example usage of simple-chromium-ai (ChromiumAI).
 * Run: node chromium_ai_example.mjs
 */

import ChromiumAI from "simple-chromium-ai";

async function simpleExample() {
  const ai = await ChromiumAI.initialize("You are a helpful assistant");
  const response = await ChromiumAI.prompt(ai, "Write a haiku");
  console.log("Simple API response:", response);
}

async function safeExample() {
  const safeResult = await ChromiumAI.Safe.initialize("You are a helpful assistant");
  return new Promise((resolve, reject) => {
    safeResult.match(
      async (ai) => {
        try {
          const safeResponse = await ChromiumAI.Safe.prompt(ai, "Write a haiku");
          safeResponse.match(
            (value) => {
              console.log("Safe API response:", value);
              resolve();
            },
            (error) => {
              console.error(error.message);
              reject(error);
            }
          );
        } catch (err) {
          reject(err);
        }
      },
      (error) => {
        console.error(error.message);
        reject(error);
      }
    );
  });
}

async function main() {
  await simpleExample();
  await safeExample();
}

main().catch(console.error);
