class Solution {
public:
    vector<int> findOrder(int n, vector<vector<int>>& pre) {
        vector<vector<int>> adj(n);
        for(auto it : pre){
            adj[it[1]].push_back(it[0]);
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
            qu.pop();
            topo.push_back(top);
            for(auto it : adj[top]){
                indegre[it]--;
                if(indegre[it] == 0) qu.push(it);
            }
        }
        if(topo.size() == n) return topo;
        return {};
    }
};
