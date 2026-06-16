const express = require('express');
const bodyParser = require('body-parser');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const app = express();
const port = process.env.PORT || 1235;

// Increase limits to handle large contexts from Claude Code
app.use(bodyParser.json({ limit: '50mb' }));
app.use(bodyParser.urlencoded({ limit: '50mb', extended: true }));

// Load API key from environment
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || '');

app.post('/v1/messages', async (req, res) => {
    const { messages, system, model, stream, max_tokens, temperature } = req.body;

    // Normalize model name - Default to gemini-2.5-flash (proven to have quota now)
    let modelName = model;
    if (!modelName || !modelName.startsWith('gemini')) {
        modelName = 'gemini-2.5-flash';
    }

    console.log(`Received request for model: ${model} (using ${modelName}), stream: ${stream}`);

    try {
        // Handle systemInstruction - Simplified to string for better SDK support
        const systemInstruction = Array.isArray(system) 
            ? system.map(s => s.text || s).join('\n') 
            : system;

        const geminiModel = genAI.getGenerativeModel({
            model: modelName,
            systemInstruction: systemInstruction || undefined,
        });

        // Convert messages to Gemini format
        const contents = messages.map(msg => ({
            role: msg.role === 'assistant' ? 'model' : 'user',
            parts: Array.isArray(msg.content) 
                ? msg.content.map(c => ({ text: c.text || c })) 
                : [{ text: msg.content }],
        }));

        if (stream) {
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');

            const result = await geminiModel.generateContentStream({
                contents,
                generationConfig: {
                    maxOutputTokens: max_tokens,
                    temperature: temperature,
                },
            });

            for await (const chunk of result.stream) {
                const chunkText = chunk.text();
                
                const response = {
                    type: 'content_block_delta',
                    index: 0,
                    delta: {
                        type: 'text_delta',
                        text: chunkText,
                    }
                };
                res.write(`data: ${JSON.stringify(response)}\n\n`);
            }

            // Final message
            res.write(`data: ${JSON.stringify({ type: 'message_stop' })}\n\n`);
            res.end();
        } else {
            const result = await geminiModel.generateContent({
                contents,
                generationConfig: {
                    maxOutputTokens: max_tokens,
                    temperature: temperature,
                },
            });

            const text = result.response.text();
            res.json({
                id: `msg_${Date.now()}`,
                type: 'message',
                role: 'assistant',
                model: model,
                content: [{ type: 'text', text }],
                stop_reason: 'end_turn',
                usage: {
                    input_tokens: 0,
                    output_tokens: 0,
                }
            });
        }
    } catch (error) {
        console.error('Error handling Gemini request:', error);
        res.status(500).json({ error: error.message });
    }
});

// Update models endpoint
app.get('/v1/models', (req, res) => {
    res.json({
        data: [
            { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
            { id: 'gemini-3-flash-preview', name: 'Gemini 3 Flash Preview' },
            { id: 'gemini-3.1-pro-preview', name: 'Gemini 3.1 Pro Preview' },
            { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
            { id: 'gemma-3-4b-it', name: 'Gemma 3 4B-it' }
        ]
    });
});

app.listen(port, () => {
    console.log(`Claude-Gemini Proxy listening at http://localhost:${port}`);
});
