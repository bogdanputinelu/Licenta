# Steps to reproduce
1. Start the Kubernetes environment (minikube version: v1.33.1) <br />`minikube start --cni calico`
2. Execute the command in cmd so that every docker command will run against the docker engine inside the minikube cluster <br /> `@FOR /f "tokens=*" %i IN ('minikube -p minikube docker-env --shell cmd') DO @%i`
3. Create Kubernetes Namespaces <br />`kubectl apply -f Namespaces`
4. Create Splunk environment
   1. Create Kubernetes Splunk instance <br />`kubectl apply -f Splunk\k8s`
   2. Port forward the Splunk Web Interface to 127.0.0.1:8001 <br />`kubectl port-forward svc/splunk 8001:8000 -n logging-namespace`
   3. Authenticate into Splunk with the account: <br />user=**admin** pass=**password**
   4. Create **centralized_api_logs** Splunk index <br /> Settings ⟶ Data ⟶ Indexes ⟶ New Index ⟶ Set Index Name to **centralized_api_logs** ⟶ Save
   5. Check if the HTTP Event Collector is enabled <br /> Settings ⟶ Data ⟶ Data Inputs ⟶ HTTP Event Collector ⟶ Global Settings ⟶ Enabled ⟶ Save
   6. Create a HEC token <br /> Settings ⟶ Data ⟶ Data Inputs ⟶ HTTP Event Collector ⟶ New Token ⟶ Set Name to FluentBit token ⟶ Next ⟶ Check Source Type is Automatic ⟶ Select Allowed Indexes centralized_api_logs ⟶ Review ⟶ Submit
   7. Copy the HEC token that was just created <br /> Settings ⟶ Data ⟶ Data Inputs ⟶ HTTP Event Collector ⟶ Copy
5. Create a Kubernetes Secret for the Splunk HEC token using the command <br /> `kubectl create secret generic splunk-hec-token --from-literal=hec-token=<SPLUNK_HEC_TOKEN> -n logging-namespace`
6. Create Kubernetes FluentBit instance <br />`kubectl apply -f FluentBit\k8s`