import torch
from .model_loader import ModelLoader
from qwen_vl_utils import process_vision_info

class InferenceEngine:
    def __init__(self, config):
        self.config = config
        self.loader = ModelLoader(config)

    def run_inference(self, messages, image, generation_config=None):
        """
        Runs inference on the loaded model.
        
        Args:
            messages (list): List of chat messages.
            image (PIL.Image): The input image (Redundant if in messages, but kept for signature compatibility).
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
        text_input = processor.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        # Process vision info (extracts images/videos from messages)
        image_inputs, video_inputs = process_vision_info(messages)
        
        # Prepare inputs
        inputs = processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(model.device)
        
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
