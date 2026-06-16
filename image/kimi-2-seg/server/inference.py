import torch
from .model_loader import ModelLoader

class InferenceEngine:
    def __init__(self, config):
        self.config = config
        self.loader = ModelLoader(config)

    def run_inference(self, messages, image, generation_config=None):
        """
        Runs inference on the loaded model.
        
        Args:
            messages (list): List of chat messages.
            image (PIL.Image): The input image.
            generation_config (dict, optional): Overrides for generation parameters.
            
        Returns:
            str: The raw generated text.
        """
        model = self.loader.get_model()
        processor = self.loader.get_processor()
        
        # Merge config
        gen_config = self.config['inference'].copy()
        if generation_config:
            gen_config.update(generation_config)

        # Apply chat template
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        
        # Prepare inputs
        inputs = processor(images=image, text=prompt, return_tensors="pt").to(model.device)
        
        # Generate
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs, 
                max_new_tokens=gen_config.get('max_new_tokens', 1024),
                do_sample=gen_config.get('do_sample', False),
                temperature=gen_config.get('temperature', 0.7)
            )
        
        # Decode response (trimming input)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        response = processor.batch_decode(
            generated_ids_trimmed, 
            skip_special_tokens=True, 
            clean_up_tokenization_spaces=False
        )[0]
        
        return response.strip()
