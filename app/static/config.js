window.APP_CONFIG = {
  "title": "CausalLab",
  "subtitle":
    "Estimate a treatment coefficient while adjusting for measured confounders.",
  "question":
    "What is the adjusted association, and is treatment overlap weak?",
  "action": "Estimate adjusted effect",
  "mapping": [
    ["outcome", "Outcome column"],
    ["treatment", "Binary treatment column (0 / 1)"]
  ],
  "multi": ["confounders", "Confounder columns"],
  "params": [],
  "note":
    "Requires at least three observations in each treatment group. A coefficient is causal only under the stated identification assumptions.",
  "sample":
    "outcome,treatment,baseline,experience\n1.8,0,0,0\n11.7,1,7,3\n5.2,0,1,6\n15.1,1,8,9\n4.2,0,2,1\n13.6,1,9,4\n7.1,0,3,7\n17.0,1,10,10\n6.1,0,4,2\n16.0,1,11,5\n9.0,0,5,8\n14.5,1,12,0\n8.0,0,6,3\n7.5,1,0,6\n11.4,0,7,9\n6.0,1,1,1\n9.9,0,8,4\n9.4,1,2,7\n13.3,0,9,10\n8.4,1,3,2\n11.8,0,10,5\n11.3,1,4,8\n10.8,0,11,0\n10.3,1,5,3\n14.2,0,12,6\n13.2,1,6,9\n2.3,0,0,1\n12.2,1,7,4\n5.7,0,1,7\n15.6,1,8,10\n4.2,0,2,2\n14.1,1,9,5\n7.6,0,3,8\n13.1,1,10,0\n6.6,0,4,3\n16.0,1,11,6\n9.5,0,5,9\n15.0,1,12,1\n8.5,0,6,4\n8.0,1,0,7\n11.4,0,7,10\n6.5,1,1,2\n10.4,0,8,5\n9.9,1,2,8\n9.4,0,9,0\n8.4,1,3,3\n12.3,0,10,6\n11.8,1,4,9\n11.3,0,11,1\n10.8,1,5,4\n14.2,0,12,7\n13.7,1,6,10\n2.8,0,0,2\n12.7,1,7,5\n6.2,0,1,8\n11.2,1,8,0\n4.7,0,2,3\n14.6,1,9,6\n8.1,0,3,9\n13.6,1,10,1\n6.6,0,4,4\n16.5,1,11,7\n10.0,0,5,10\n15.5,1,12,2\n9.0,0,6,5\n8.0,1,0,8\n7.5,0,7,0\n7.0,1,1,3\n10.9,0,8,6\n10.4,1,2,9\n9.4,0,9,1\n8.9,1,3,4\n12.8,0,10,7\n12.3,1,4,10\n11.8,0,11,2\n10.8,1,5,5\n14.7,0,12,8\n9.8,1,6,0\n3.3,0,0,3\n13.2,1,7,6\n",
  "slug": "causallab"
};
