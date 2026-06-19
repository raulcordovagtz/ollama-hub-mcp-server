#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { search as ddgWebSearch, searchImages as ddgImageSearch, SafeSearchType } from "duck-duck-scrape";

const server = new Server({
    name: "search-hub-mcp",
    version: "1.0.0",
}, {
    capabilities: {
        tools: {},
    },
});

// Configurable SearXNG instance (fallback to searx.be if not provided)
const SEARXNG_INSTANCE = process.env.SEARXNG_URL || "https://searx.be";

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "searxng_search",
                description: "Search Google and other search engines anonymously using SearXNG. Returns privacy-respecting results.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: { type: "string", description: "The search query" },
                        page: { type: "number", description: "Page number to retrieve (default: 1)" }
                    },
                    required: ["query"],
                },
            },
            {
                name: "duckduckgo_web_search",
                description: "Search the web using DuckDuckGo.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: { type: "string", description: "The search query" },
                        safeSearch: { type: "string", enum: ["strict", "moderate", "off"], description: "Safe Search level (default: moderate)" }
                    },
                    required: ["query"],
                },
            },
            {
                name: "duckduckgo_image_search",
                description: "Search for images using DuckDuckGo.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: { type: "string", description: "The image search query" },
                        safeSearch: { type: "string", enum: ["strict", "moderate", "off"], description: "Safe Search level (default: moderate)" }
                    },
                    required: ["query"],
                },
            }
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
        const { name, arguments: args } = request.params;

        if (name === "searxng_search") {
            const query = args?.query as string;
            const page = args?.page as number || 1;
            if (!query) throw new Error("query is required");

            const url = `${SEARXNG_INSTANCE}/search?q=${encodeURIComponent(query)}&format=json&pageno=${page}`;
            
            // Randomly pick a realistic user agent to avoid being blocked by instances
            const uas = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
            ];
            
            const response = await fetch(url, {
                headers: {
                    "User-Agent": uas[Math.floor(Math.random() * uas.length)],
                    "Accept": "application/json"
                }
            });

            if (!response.ok) {
                throw new Error(`SearXNG API returned ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const results = data.results || [];
            
            if (results.length === 0) {
                return { content: [{ type: "text", text: "No results found." }] };
            }

            const formattedResults = results.map((r: any, index: number) => {
                return `[${index + 1}] ${r.title}\nURL: ${r.url}\nSnippet: ${r.content || r.parsed_url}\n`;
            }).join("\n");

            return {
                content: [{ type: "text", text: `SearXNG Results for "${query}":\n\n${formattedResults}` }],
            };
        }

        if (name === "duckduckgo_web_search") {
            const query = args?.query as string;
            if (!query) throw new Error("query is required");
            const safeSearchStr = args?.safeSearch as string || "moderate";
            const safeSearch = safeSearchStr === "strict" ? SafeSearchType.STRICT : 
                               safeSearchStr === "off" ? SafeSearchType.OFF : SafeSearchType.MODERATE;

            const results = await ddgWebSearch(query, { safeSearch });
            const formattedResults = results.results.slice(0, 10).map((r, i) => {
                return `[${i + 1}] ${r.title}\nURL: ${r.url}\nSnippet: ${r.description}\n`;
            }).join("\n");

            return {
                content: [{ type: "text", text: formattedResults || "No results found." }]
            };
        }

        if (name === "duckduckgo_image_search") {
            const query = args?.query as string;
            if (!query) throw new Error("query is required");
            const safeSearchStr = args?.safeSearch as string || "moderate";
            const safeSearch = safeSearchStr === "strict" ? SafeSearchType.STRICT : 
                               safeSearchStr === "off" ? SafeSearchType.OFF : SafeSearchType.MODERATE;

            const results = await ddgImageSearch(query, { safeSearch });
            const formattedResults = results.results.slice(0, 10).map((r, i) => {
                return `[${i + 1}] ${r.title}\nImage URL: ${r.image}\nSource URL: ${r.url}\n`;
            }).join("\n");

            return {
                content: [{ type: "text", text: formattedResults || "No images found." }]
            };
        }

        throw new Error(`Unknown tool: ${name}`);

    } catch (error: any) {
        return {
            content: [{ type: "text", text: `Error: ${error.message}` }],
            isError: true,
        };
    }
});

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Search Hub MCP Server running on stdio");
}

main().catch((err) => {
    console.error("Fatal error starting Search Hub:", err);
    process.exit(1);
});
