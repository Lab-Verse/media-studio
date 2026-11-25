"""Memory-saving prompt caches must remain exact and non-executable."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
import torch
from safetensors.torch import save_file
from engine import ai_fallback as ai

class PromptCacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.env=patch.dict(os.environ,{'IMAGE_PROMPT_CACHE':str(self.root)},clear=True);self.env.start()
  self.args=('a rain-streaked window','flux2_klein','selected-model',128)
  self.key=ai.prompt_cache_key(*self.args)
 def tearDown(self):self.env.stop();self.tmp.cleanup();ai._load.cache_clear()
 def save(self,tensor=None,metadata=None):
  save_file({'prompt_embeds':torch.ones((1,128,16))if tensor is None else tensor},str(self.root/(self.key+'.safetensors')),metadata={'cache_key':self.key}if metadata is None else metadata)
 def test_roundtrip_is_cpu_and_key_binds_contract(self):
  self.save();self.assertEqual(tuple(ai.cached_prompt(*self.args).shape),(1,128,16))
  for args in [('changed prompt',*self.args[1:]),(self.args[0],'flux',*self.args[2:]),(*self.args[:2],'another-model',128),(*self.args[:3],64)]:
   self.assertNotEqual(self.key,ai.prompt_cache_key(*args))
   with self.assertRaises(FileNotFoundError):ai.cached_prompt(*args)
 def test_wrong_metadata_rejected(self):
  self.save(metadata={'cache_key':'other'})
  with self.assertRaisesRegex(ValueError,'metadata'):ai.cached_prompt(*self.args)
  save_file({'prompt_embeds':torch.ones((1,128,16))},str(self.root/(self.key+'.safetensors')))
  with self.assertRaisesRegex(ValueError,'metadata'):ai.cached_prompt(*self.args)
 def test_nonfinite_or_invalid_shape_rejected(self):
  for tensor in [torch.full((1,128,16),float('nan')),torch.ones((2,128,16)),torch.ones((1,129,16)),torch.ones((1,128,16),dtype=torch.int64),torch.ones((1,0,16))]:
   self.save(tensor)
   with self.assertRaisesRegex(ValueError,'Invalid'):ai.cached_prompt(*self.args)
 def test_symlink_rejected(self):
  outside=self.root/'other.safetensors';save_file({'prompt_embeds':torch.ones((1,128,16))},str(outside))
  (self.root/(self.key+'.safetensors')).symlink_to(outside)
  with self.assertRaisesRegex(ValueError,'Unsafe'):ai.cached_prompt(*self.args)
 def test_cached_loader_excludes_text_model(self):
  pipe=MagicMock()
  with patch('diffusers.Flux2KleinPipeline.from_pretrained',return_value=pipe)as load:
   ai._load('flux2_klein','selected-model','cuda',True,None)
  self.assertIsNone(load.call_args.kwargs['text_encoder'])
  pipe.enable_model_cpu_offload.assert_called_once_with(device='cuda')
 def test_default_loader_keeps_existing_contract(self):
  del os.environ['IMAGE_PROMPT_CACHE'];os.environ['IMAGE_TEXT_DEVICE']='cpu'
  with patch('diffusers.Flux2KleinPipeline.from_pretrained',return_value=MagicMock())as load:
   ai._load('flux2_klein','selected-model','cuda',True,None)
  self.assertNotIn('text_encoder',load.call_args.kwargs)
 def test_sequential_loader_moves_smaller_modules(self):
  os.environ['IMAGE_OFFLOAD_MODE']='sequential';pipe=MagicMock()
  with patch('diffusers.Flux2KleinPipeline.from_pretrained',return_value=pipe):
   ai._load('flux2_klein','selected-model','cuda',True,None)
  pipe.enable_sequential_cpu_offload.assert_called_once_with(device='cuda')
  pipe.enable_model_cpu_offload.assert_not_called()

if __name__=='__main__':unittest.main()
