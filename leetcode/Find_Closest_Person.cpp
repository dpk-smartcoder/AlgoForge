class Solution {
public:
    int findClosest(int x, int y, int z) {
        int xzDist = abs(x-z);
        int yzDist = abs(y-z);
        if(xzDist < yzDist){
            return 1;
        }else if(xzDist > yzDist){
            return 2;
        }
        return 0;
    }
};