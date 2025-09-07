class Solution {
public:
    bool canFinish(int n, vector<vector<int>>& pre) {
        vector<vector<int>> adj(n);
        for(auto it : pre){
            adj[it[0]].push_back(it[1]);
        }

        vector<int> indegre(n,0);
        for(int i=0; i<n; i++){
            for(auto it : adj[i]){
                indegre[it]++;
            }
        }
        queue<int> qu;
        for(int i=0; i<n; i++){
            if(indegre[i] == 0){
                qu.push(i);
            }
        }
        vector<int> topo;
        while(!qu.empty()){
            int top = qu.front();
            topo.push_back(top);
            qu.pop();
            for(auto it : adj[top]){
                indegre[it]--;
                if(indegre[it] == 0) qu.push(it);
            }
        }
        return (topo.size() == n);
    }
};