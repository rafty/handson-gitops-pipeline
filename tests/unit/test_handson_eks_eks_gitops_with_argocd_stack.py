import aws_cdk as core
import aws_cdk.assertions as assertions

from handson_eks_eks_gitops_with_argocd.handson_eks_eks_gitops_with_argocd_stack import HandsonEksEksGitopsWithArgocdStack

# example tests. To run these tests, uncomment this file along with the example
# resource in handson_eks_eks_gitops_with_argocd/handson_eks_eks_gitops_with_argocd_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = HandsonEksEksGitopsWithArgocdStack(app, "handson-eks-eks-gitops-with-argocd")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
