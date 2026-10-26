"""terraform is not installed in CI here, so these are static guards on the
security posture of the config, not a substitute for `terraform validate`."""
import os
import re
import unittest

TF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy", "terraform")


def read(name):
    with open(os.path.join(TF, name), encoding="utf-8") as fh:
        return fh.read()


class TerraformGuards(unittest.TestCase):
    def setUp(self):
        self.main, self.vars = read("main.tf"), read("variables.tf")

    def test_imds_v2_only_with_hop_limit_one(self):
        self.assertIn('http_tokens                 = "required"', self.main)
        self.assertRegex(self.main, r"http_put_response_hop_limit\s*=\s*1\b")

    def test_no_instance_role(self):
        self.assertNotIn("iam_instance_profile", re.sub(r"#.*", "", self.main))

    def test_ingress_only_from_variable_never_world(self):
        ingress = re.findall(r"ingress\s*\{.*?\n\s*\}", self.main, re.S)
        self.assertTrue(ingress)
        for block in ingress:
            self.assertIn("var.allowed_cidr", block)
            self.assertNotIn("0.0.0.0/0", block)

    def test_allowed_cidr_has_no_default_and_rejects_open(self):
        block = re.search(r'variable "allowed_cidr" \{.*?\n\}', self.vars, re.S).group(0)
        self.assertNotRegex(block, r"(?m)^\s*default\s*=")
        self.assertIn('!= "0.0.0.0/0"', block)

    def test_api_key_is_sensitive_and_encrypted_disk(self):
        self.assertRegex(re.search(r'variable "worker_api_key" \{.*?\n\}', self.vars, re.S).group(0),
                         r"sensitive\s*=\s*true")
        self.assertIn("encrypted   = true", self.main)

    def test_state_and_secrets_gitignored(self):
        with open(os.path.join(TF, "..", "..", ".gitignore")) as fh:
            ig = fh.read()
        for pat in ("*.tfstate*", "terraform.tfvars"):
            self.assertIn(pat, ig)


if __name__ == "__main__":
    unittest.main()
