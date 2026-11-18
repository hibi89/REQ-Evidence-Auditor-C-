"""C-01..03 isolated unit smoke for frozen reqea.v1 inputs."""
import os
import sys
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from reqea_evidence.matcher import match_requirement, normalize_index_files
from reqea_evidence.classify import classify
from reqea_evidence.provenance import provenance, limited_scan

class UnitTests(unittest.TestCase):
    def test_exact_path_and_symbol(self):
        files, warnings = normalize_index_files({'files': [{'path': 'src/x.py', 'sha256': 'a'*64,
            'language': 'python', 'symbols': [{'name':'run','line':7}]}]})
        self.assertFalse(warnings)
        req={'req_id':'REQ-019', 'explicit_refs':['src/x.py:run'],
             'acceptance_criteria':['src/x.py:run', 'behavior unknown']}
        found=match_requirement(req, files, 'b'*40)
        self.assertEqual(found['evidence'][0]['symbol'], 'run')
        self.assertEqual(found['criteria'][1]['status'], 'UNASSESSED')
        self.assertEqual(classify(found, incomplete=False, sha_mismatch=False), 'CODE_CANDIDATE')

    def test_sha_and_truncated_block(self):
        mismatch, warn = provenance({'source_sha':'a'*40},{'source_sha':'b'*40}, {})
        self.assertTrue(mismatch)
        self.assertIn('SOURCE_SHA_MISMATCH', warn)
        incomplete, _ = limited_scan({'limits':{'truncated':True,'scanned_files':0,'skipped_files':0},'warnings':[]})
        self.assertTrue(incomplete)
        self.assertEqual(classify({'warnings':[], 'criteria':[{'criterion':'x','status':'UNASSESSED'}],
                      'evidence':[], 'missing_refs':['src/missing.py'], 'ref_count':1},
                      incomplete=True, sha_mismatch=False), 'UNASSESSED')

    def test_conflicting_hash_never_reused(self):
        files, warnings=normalize_index_files({'files':[{'path':'x.py','sha256':'a'*64},
            {'path':'x.py','sha256':'b'*64},{'path':'x.py','sha256':'a'*64}]})
        self.assertNotIn('x.py', files)
        self.assertIn('CONFLICTING_FILE_HASH', warnings)

if __name__ == '__main__': unittest.main()
