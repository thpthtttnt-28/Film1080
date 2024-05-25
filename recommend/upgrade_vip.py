from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest
import os
from django.views.decorators.csrf import csrf_exempt

class UpgradeVIP(LoginRequiredMixin, TemplateView):
    template_name = 'recommend/upgrade_vip.html'

    def post(self, request, *args, **kwargs):
        user_profile = request.user.userprofile
        user_profile.is_vip = True
        user_profile.save()
        return redirect('profile')
    
class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv('PAYPAL_CLIENT_ID')
        self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
        self.environment = SandboxEnvironment(client_id=self.client_id, client_secret=self.client_secret)
        self.client = PayPalHttpClient(self.environment)

class UpgradeToVIP(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        amount = "10.00"
        if request.POST.get('payment_method') == 'manual':
            request.user.userprofile.is_vip = True
            request.user.userprofile.save()
            return redirect('success')
        else:
            paypal_client = PayPalClient()
            request = OrdersCreateRequest()
            request.prefer("return=representation")
            request.request_body({
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": amount
                    }
                }]
            })

            response = paypal_client.client.execute(request)
            for link in response.result.links:
                if link.rel == "approve":
                    approval_url = link.href
                    return redirect(approval_url)