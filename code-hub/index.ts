#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { spawn, exec } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import * as crypto from "crypto";
import * as dotenv from "dotenv";

// 1. Session Management
const sessionDir = path.join(os.tmpdir(), `code-hub-session-${crypto.randomUUID()}`);
fs.mkdirSync(sessionDir, { recursive: true });

function cleanup() {
    try {
        if (fs.existsSync(sessionDir)) {
            fs.rmSync(sessionDir, { recursive: true, force: true });
        }
    } catch (e) {
        // Silent cleanup error
    }
}

process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(0); });
process.on('SIGTERM', () => { cleanup(); process.exit(0); });
process.on('uncaughtException', (err) => {
    console.error("Uncaught exception:", err);
    cleanup();
    process.exit(1);
});

// 2. Python Sandbox Environment Setup
const VENV_PATH = path.join(os.homedir(), ".lmstudio", "python-sandbox-venv");
const PYTHON_BIN = process.platform === "win32" ? path.join(VENV_PATH, "Scripts", "python.exe") : path.join(VENV_PATH, "bin", "python");

function ensurePythonVenv() {
    if (!fs.existsSync(VENV_PATH)) {
        console.error(`Creating Python virtual environment at ${VENV_PATH}...`);
        const pythonBase = process.platform === "win32" ? "python" : "python3";
        require("child_process").execSync(`${pythonBase} -m venv "${VENV_PATH}"`, { stdio: "inherit" });
    }
}

// Read Global Env
const envFilePath = path.join(os.homedir(), "desarrollo-local", "server", "sandbox.env");
const globalEnvConfig = fs.existsSync(envFilePath) ? dotenv.parse(fs.readFileSync(envFilePath)) : {};

function getInjectedEnv(isPython: boolean = false) {
    const envVars = { ...process.env, ...globalEnvConfig };
    if (isPython) {
        envVars["VIRTUAL_ENV"] = VENV_PATH;
        const binPath = process.platform === "win32" ? path.join(VENV_PATH, "Scripts") : path.join(VENV_PATH, "bin");
        envVars["PATH"] = `${binPath}:${process.env.PATH || ""}`;
    }
    return envVars;
}

// 3. Server Setup
const server = new Server({
    name: "code-hub-mcp",
    version: "1.0.0",
}, {
    capabilities: {
        tools: {},
    },
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "execute_python",
                description: "Run a Python script. Shares a temporary working directory with other languages. Retains state in a shared virtual environment.",
                inputSchema: {
                    type: "object",
                    properties: {
                        code: { type: "string", description: "The Python code to run" }
                    },
                    required: ["code"],
                },
            },
            {
                name: "execute_js",
                description: "Run a JavaScript script via Node.js. Shares the temporary working directory with other languages.",
                inputSchema: {
                    type: "object",
                    properties: {
                        code: { type: "string", description: "The JavaScript code to run" }
                    },
                    required: ["code"],
                },
            },
            {
                name: "execute_applescript",
                description: "Run an AppleScript via osascript. Very powerful for controlling the Mac (Finder, Safari, System Events).",
                inputSchema: {
                    type: "object",
                    properties: {
                        code: { type: "string", description: "The AppleScript code to run" }
                    },
                    required: ["code"],
                },
            },
            {
                name: "execute_bash",
                description: "Run a bash command. Has full power over the system. Shares the temporary working directory.",
                inputSchema: {
                    type: "object",
                    properties: {
                        command: { type: "string", description: "The bash command to run" }
                    },
                    required: ["command"],
                },
            }
        ],
    };
});

async function runChildProcess(cmd: string, args: string[], env: any): Promise<{stdout: string, stderr: string}> {
    return new Promise((resolve, reject) => {
        const child = spawn(cmd, args, {
            cwd: sessionDir,
            env,
            stdio: "pipe",
            timeout: 120000 // 2 minutes timeout
        });

        let stdout = "";
        let stderr = "";
        child.stdout.setEncoding("utf-8");
        child.stderr.setEncoding("utf-8");
        child.stdout.on("data", data => stdout += data);
        child.stderr.on("data", data => stderr += data);

        child.on("close", code => {
            if (code === 0) {
                resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
            } else {
                reject(new Error(`Exit code ${code}\\nStderr:\\n${stderr.trim()}`));
            }
        });
        child.on("error", err => reject(err));
    });
}

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
        const { name, arguments: args } = request.params;

        if (name === "execute_python") {
            ensurePythonVenv();
            const code = args?.code as string;
            if (!code) throw new Error("code is required");
            const scriptPath = path.join(sessionDir, `script_${Date.now()}.py`);
            fs.writeFileSync(scriptPath, code, "utf-8");
            const result = await runChildProcess(PYTHON_BIN, [scriptPath], getInjectedEnv(true));
            return { content: [{ type: "text", text: `Stdout:\n${result.stdout}\n\nStderr:\n${result.stderr}` }] };
        }

        if (name === "execute_js") {
            const code = args?.code as string;
            if (!code) throw new Error("code is required");
            const scriptPath = path.join(sessionDir, `script_${Date.now()}.js`);
            fs.writeFileSync(scriptPath, code, "utf-8");
            const result = await runChildProcess("node", [scriptPath], getInjectedEnv(false));
            return { content: [{ type: "text", text: `Stdout:\n${result.stdout}\n\nStderr:\n${result.stderr}` }] };
        }

        if (name === "execute_applescript") {
            const code = args?.code as string;
            if (!code) throw new Error("code is required");
            const scriptPath = path.join(sessionDir, `script_${Date.now()}.scpt`);
            fs.writeFileSync(scriptPath, code, "utf-8");
            const result = await runChildProcess("osascript", [scriptPath], getInjectedEnv(false));
            return { content: [{ type: "text", text: `Stdout:\n${result.stdout}\n\nStderr:\n${result.stderr}` }] };
        }

        if (name === "execute_bash") {
            const command = args?.command as string;
            if (!command) throw new Error("command is required");
            const env = getInjectedEnv(false);
            return new Promise((resolve, reject) => {
                exec(command, { cwd: sessionDir, env, timeout: 120000 }, (error, stdout, stderr) => {
                    if (error) {
                        resolve({ content: [{ type: "text", text: `Error: ${error.message}\nStdout:\n${stdout.trim()}\nStderr:\n${stderr.trim()}` }] });
                    } else {
                        resolve({ content: [{ type: "text", text: `Stdout:\n${stdout.trim()}\n\nStderr:\n${stderr.trim()}` }] });
                    }
                });
            });
        }

        throw new Error(`Unknown tool: ${name}`);

    } catch (error: any) {
        return {
            content: [{ type: "text", text: `Error executing tool: ${error.message}` }],
            isError: true,
        };
    }
});

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error(`Code Hub MCP Server running on stdio`);
    console.error(`Session directory: ${sessionDir}`);
}

main().catch((err) => {
    console.error("Fatal error starting Code Hub:", err);
    cleanup();
    process.exit(1);
});
