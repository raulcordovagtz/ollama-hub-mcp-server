const { GoogleGenerativeAI } = require('@google/generative-ai');
const genAI = new GoogleGenerativeAI('AIzaSyCjMST4Za73f0v1Jgjac9hdeQXAL5pIT_o');

async function listModels() {
    try {
        const result = await genAI.getGenerativeModel({ model: 'gemini-1.5-flash' }).listModels();
        console.log(JSON.stringify(result, null, 2));
    } catch (e) {
        // Fallback or detailed error
        console.error(e);
    }
}
listModels();
